
import sqlite3
import json
import re
import math
from collections import Counter
from typing import List, Dict, Any, Tuple, Set
from concurrent.futures import ProcessPoolExecutor
import os

from core.utils.geo_utils import haversine_distance, calculate_geo_score

# Pre-compile regex for speed
WORD_PATTERN = re.compile(r'\w+')

class CompositeMatcher:
    """
    Advanced matching engine that combines multiple scoring factors:
    - Identity Core (Age, Sex, Race)
    - Keyword Specificity (TF-IDF overlap)
    - Geographic Proximity (Haversine decay)
    - Biological Evidence (DNA/Dental status)
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.stop_words = {
            'the', 'and', 'was', 'with', 'found', 'on', 'in', 'at', 'of', 'for', 'to', 'is', 'has', 
            'unknown', 'unsure', 'uncertain', 'years', 'old', 'male', 'female', 'white', 'black', 
            'caucasian', 'american', 'african', 'hispanic', 'asian', 'native', 'race', 'sex', 
            'estimated', 'approximately', 'approx', 'about', 'inches', 'pounds', 'cm', 'kg', 'lbs',
            'body', 'description', 'subject', 'case', 'number', 'discovery', 'location', 'found',
            'sighting', 'last', 'seen', 'contact', 'date', 'remains', 'charred', 'skeletonized',
            'burned', 'discovered', 'debris', 'underneath', 'after', 'before', 'around', 'above',
            'below', 'where', 'which', 'there', 'their', 'them', 'they', 'this', 'that', 'from',
            'into', 'been', 'were', 'also', 'some', 'many', 'very', 'small', 'large', 'water',
            'side', 'both', 'between', 'area', 'name', 'time', 'well', 'worn', 'long', 'size',
            'brand', 'color', 'black', 'white', 'blue', 'red', 'green', 'yellow', 'brown', 'gray'
        }
        self.idf_cache = {}
        self.uhr_total = 0
        self.mp_total = 0
        self.uhr_df = Counter()
        self.mp_df = Counter()

    def _get_words(self, text: str) -> Set[str]:
        if not text: return set()
        words = set(WORD_PATTERN.findall(text.lower()))
        # Filter: Min 3 chars, and avoid pure numeric IDs unless very specific
        filtered = {w for w in words if len(w) > 2 and not w.isdigit()}
        return filtered

    def load_stats(self, conn: sqlite3.Connection):
        """Pre-calculate global statistics for TF-IDF."""
        print("Loading global TF-IDF statistics")
        cursor = conn.cursor()
        
        # UHR stats
        cursor.execute("SELECT description FROM unidentified_cases")
        for i, row in enumerate(cursor.fetchall()):
            if row[0]:
                self.uhr_total += 1
                words = self._get_words(row[0]) - self.stop_words
                for word in words:
                    self.uhr_df[word] += 1
            if i % 5000 == 0 and i > 0: print(f"  Summarized {i} UHR cases")
        
        # MP stats
        cursor.execute("SELECT description FROM missing_persons")
        for i, row in enumerate(cursor.fetchall()):
            if row[0]:
                self.mp_total += 1
                words = self._get_words(row[0]) - self.stop_words
                for word in words:
                    self.mp_df[word] += 1
            if i % 10000 == 0 and i > 0: print(f"  Summarized {i} MP cases")
        print(f"Stats loaded. UHR: {self.uhr_total}, MP: {self.mp_total}")

    def calculate_specificity(self, word: str, df: Counter, total_docs: int) -> float:
        if word in self.stop_words: return 0.0
        count = df.get(word, 0)
        if count <= 0: return 2.5 # Extremely rare
        return math.log10(total_docs / count)

    def score_text_overlap(
        self, 
        words1: Set[str], 
        words2: Set[str], 
    ) -> Tuple[float, List[str]]:
        common = words1 & words2
        if not common:
            return 0.0, []
        
        total_score = 0.0
        matched_features = []
        for word in common:
            if word not in self.idf_cache:
                spec1 = self.calculate_specificity(word, self.uhr_df, self.uhr_total)
                spec2 = self.calculate_specificity(word, self.mp_df, self.mp_total)
                self.idf_cache[word] = (spec1 + spec2) / 2
            
            specificity = self.idf_cache[word]
            total_score += specificity
            
            # Hardened thresholds. Rare: >2.2, Normal: >1.5
            if specificity > 2.2:
                matched_features.append(f"{word} (Rare)")
            elif specificity > 1.5:
                matched_features.append(word)
        
        return min(1.0, total_score / 35), matched_features

    def calculate_phenotypic_score(self, u_race: str, m_race: str) -> float:
        score = 0.0
        if u_race and m_race:
            score += 0.5 if u_race == m_race else 0.0
        return min(1.0, score * 2)

    def calculate_bio_multiplier(self, u_dna: str, u_dental: str, m_dna: str, m_dental: str) -> float:
        dna_ready = u_dna == 'Complete' and m_dna == 'Complete'
        dental_ready = u_dental == 'Complete' and m_dental == 'Complete'
        if dna_ready or dental_ready:
            return 1.5
        return 1.0

    def find_leads(
        self, 
        min_score: float = 0.35, 
        limit: int = 200,
        parallel: bool = True
    ) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        try:
            self.load_stats(conn)
            
            cursor = conn.cursor()
            cursor.execute("""
                SELECT case_number, estimated_sex, estimated_age_min, estimated_age_max, 
                       discovery_date, description, discovery_lat, discovery_lon, race, dna_status, dental_status
                FROM unidentified_cases 
            """)
            uhr_cases = cursor.fetchall()
            
            # Pre-process UHR cases (sets of words)
            processed_uhr = []
            for uhr in uhr_cases:
                u_num, u_sex, u_age_min, u_age_max, u_date, u_desc, u_lat, u_lon, u_race, u_dna, u_dental = uhr
                u_words = self._get_words(u_desc) - self.stop_words
                
                processed_uhr.append({
                    "u_num": u_num, "u_sex": u_sex, "u_age_min": u_age_min, "u_age_max": u_age_max,
                    "u_date": u_date, "u_desc": u_desc, "u_words": u_words, "u_lat": u_lat, "u_lon": u_lon,
                    "u_race": u_race, "u_dna": u_dna, "u_dental": u_dental
                })

            # Stats to share with workers (to avoid recalculating IDF)
            stats = {
                "uhr_df": self.uhr_df, "mp_df": self.mp_df,
                "uhr_total": self.uhr_total, "mp_total": self.mp_total,
                "idf_cache": self.idf_cache
            }

            if parallel:
                num_workers = os.cpu_count() or 4
                chunk_size = max(1, len(processed_uhr) // num_workers)
                chunks = [processed_uhr[i:i + chunk_size] for i in range(0, len(processed_uhr), chunk_size)]
                
                all_leads = []
                with ProcessPoolExecutor(max_workers=num_workers) as executor:
                    # Pass stats dictionary to workers
                    futures = [executor.submit(self._match_chunk, chunk, stats, min_score) for chunk in chunks]
                    for future in futures:
                        all_leads.extend(future.result())
            else:
                all_leads = self._match_chunk(processed_uhr, stats, min_score)
                
            all_leads.sort(key=lambda x: x['score'], reverse=True)
            return all_leads[:limit]
        finally:
            conn.close()

    def _match_chunk(self, uhr_subset: List[Dict[str, Any]], stats: Dict[str, Any], min_score: float) -> List[Dict[str, Any]]:
        """Worker function for parallel matching with database streaming."""
        # Update worker instance with shared stats
        self.uhr_df = stats["uhr_df"]
        self.mp_df = stats["mp_df"]
        self.uhr_total = stats["uhr_total"]
        self.mp_total = stats["mp_total"]
        self.idf_cache = stats["idf_cache"]
        
        results = []
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            for u in uhr_subset:
                u_date_limit = u["u_date"] if u["u_date"] else '9999-12-31'
                
                # Build SQL filter for candidates
                # Initial filter: Date, Sex, and Bounding Box
                query = """
                    SELECT file_number, name, age_at_disappearance, last_seen_date, 
                           description, last_seen_lat, last_seen_lon, sex, race, dna_status, dental_status
                    FROM missing_persons
                    WHERE (last_seen_date IS NULL OR last_seen_date <= ?)
                """
                params = [u_date_limit]
                
                if u["u_sex"] and u["u_sex"] not in ('Uncertain', 'Unknown'):
                    query += " AND (sex IS NULL OR sex IN ('Unknown', 'Uncertain', ?))"
                    params.append(u["u_sex"])
                
                if u["u_lat"] is not None and u["u_lon"] is not None:
                    query += " AND (last_seen_lat IS NULL OR (last_seen_lat BETWEEN ? AND ? AND last_seen_lon BETWEEN ? AND ?))"
                    params.extend([u["u_lat"] - 8, u["u_lat"] + 8, u["u_lon"] - 8, u["u_lon"] + 8])

                cursor.execute(query, params)
                
                for row in cursor.fetchall():
                    m_num, m_name, m_age, m_date, m_desc, m_lat, m_lon, m_sex, m_race, m_dna, m_dental = row
                    
                    # 4. Age Filter (Hard exclusion)
                    if u["u_age_min"] and m_age and (m_age < u["u_age_min"] - 10 or (u["u_age_max"] and m_age > u["u_age_max"] + 10)):
                        continue
                    
                    # 5. Keyword Overlap (TF-IDF)
                    m_words = self._get_words(m_desc) - self.stop_words
                    text_score, features = self.score_text_overlap(u["u_words"], m_words)
                    
                    # 6. Geographic Decay
                    dist = haversine_distance(u["u_lat"], u["u_lon"], m_lat, m_lon)
                    geo_score = calculate_geo_score(dist)
                    
                    # 7. Phenotypic Matching
                    pheno_score = self.calculate_phenotypic_score(u["u_race"], m_race)
                    
                    # 8. Composite Scoring
                    composite_score = (text_score * 0.4) + (geo_score * 0.3) + (pheno_score * 0.3)
                    
                    # 9. Biological Multiplier
                    multiplier = self.calculate_bio_multiplier(u["u_dna"], u["u_dental"], m_dna, m_dental)
                    final_score = min(1.0, composite_score * multiplier)
                    
                    if final_score >= min_score:
                        report_features = features.copy()
                        if dist is not None:
                            report_features.append(f"{int(dist)} miles away")
                        
                        results.append({
                            "uhr_case": u["u_num"],
                            "mp_file": m_num,
                            "mp_name": m_name,
                            "score": round(final_score, 3),
                            "shared_features": report_features,
                            "uhr_desc_preview": u["u_desc"][:200],
                            "mp_desc_preview": m_desc[:200]
                        })
        finally:
            conn.close()
            
        return results
