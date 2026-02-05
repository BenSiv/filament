
import sqlite3
import json
import re
import math
from collections import Counter
from typing import List, Dict, Any, Tuple, Set

class SpecificityMatcher:
    """
    Advanced matching logic based on keyword specificity (IDF-like scoring).
    Surfaces leads by prioritizing rare identifiers over common ones.
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
            'burned', 'discovered', 'debris', 'underneath', 'after', 'before', 'around'
        }
        
    def get_word_frequencies(self, conn: sqlite3.Connection, table_name: str, column_name: str) -> Tuple[Counter, int]:
        """Calculate document frequency for words in a table/column."""
        cursor = conn.cursor()
        cursor.execute(f"SELECT {column_name} FROM {table_name}")
        
        doc_count = 0
        df = Counter()
        
        for row in cursor.fetchall():
            if row[0]:
                doc_count += 1
                words = set(re.findall(r'\w+', row[0].lower()))
                for word in words:
                    df[word] += 1
                    
        return df, doc_count

    def calculate_specificity(self, word: str, df: Counter, total_docs: int) -> float:
        """Calculate specificity score (log-inverse frequency)."""
        count = df.get(word, 0)
        if count == 0: return 2.0
        return math.log10(total_docs / count)

    def score_text_overlap(
        self, 
        text1: str, 
        text2: str, 
        df1: Counter, 
        df2: Counter, 
        total1: int, 
        total2: int
    ) -> Tuple[float, List[str]]:
        """Score overlap between two texts, weighting by specificity."""
        if not text1 or not text2:
            return 0.0, []
            
        words1 = set(re.findall(r'\w+', text1.lower())) - self.stop_words
        words2 = set(re.findall(r'\w+', text2.lower())) - self.stop_words
        
        common = words1 & words2
        if not common:
            return 0.0, []
            
        total_score = 0.0
        matched_features = []
        
        for word in common:
            spec1 = self.calculate_specificity(word, df1, total1)
            spec2 = self.calculate_specificity(word, df2, total2)
            specificity = (spec1 + spec2) / 2
            
            # Exponentially weight specificity to favor rare words
            weight = math.pow(10, specificity - 1.0) if specificity > 1.0 else specificity
            total_score += weight
            
            if specificity > 1.8:
                matched_features.append(f"{word} (Rare)")
            elif specificity > 1.2:
                matched_features.append(word)
                
        return min(1.0, total_score / 50), matched_features

    def find_leads(
        self, 
        min_score: float = 0.4, 
        limit: int = 200, 
        uhr_min_desc_len: int = 50
    ) -> List[Dict[str, Any]]:
        """Perform batch matching across the database to find strong leads."""
        conn = sqlite3.connect(self.db_path)
        try:
            uhr_df, uhr_total = self.get_word_frequencies(conn, "unidentified_cases", "description")
            mp_df, mp_total = self.get_word_frequencies(conn, "missing_persons", "description")
            
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT id, case_number, estimated_sex, estimated_age_min, estimated_age_max, discovery_date, description 
                FROM unidentified_cases 
                WHERE length(description) > {uhr_min_desc_len}
            """)
            uhr_cases = cursor.fetchall()
            
            all_leads = []
            for uhr in uhr_cases:
                u_id, u_num, u_sex, u_age_min, u_age_max, u_date, u_desc = uhr
                
                query = "SELECT id, file_number, name, sex, age_at_disappearance, last_seen_date, description FROM missing_persons WHERE (last_seen_date IS NULL OR last_seen_date <= ?)"
                params = [u_date if u_date else '9999-12-31']
                
                if u_sex and u_sex != 'Uncertain':
                    query += " AND (sex IS NULL OR sex = 'Unknown' OR sex = 'Uncertain' OR sex = ?)"
                    params.append(u_sex)
                    
                cursor.execute(query, params)
                candidates = cursor.fetchall()
                
                for cand in candidates:
                    m_id, m_num, m_name, m_sex, m_age, m_date, m_desc = cand
                    
                    if u_age_min and m_age and abs(u_age_min - m_age) > 20:
                        continue
                        
                    score, features = self.score_text_overlap(u_desc, m_desc, uhr_df, mp_df, uhr_total, mp_total)
                    
                    if score >= min_score:
                        all_leads.append({
                            "uhr_case": u_num,
                            "mp_file": m_num,
                            "mp_name": m_name,
                            "score": round(score, 3),
                            "shared_features": features,
                            "uhr_desc_preview": u_desc[:200] + "...",
                            "mp_desc_preview": m_desc[:200] + "..."
                        })
                
                if len(all_leads) > limit * 5: break # Partial safety cap
                
            all_leads.sort(key=lambda x: x['score'], reverse=True)
            return all_leads[:limit]
        finally:
            conn.close()
