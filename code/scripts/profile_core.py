
import cProfile
import pstats
import io
import sys
import os

# Ensure the code directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.search import CompositeMatcher

def profile_matcher():
    db_path = "data/filament.db"
    matcher = CompositeMatcher(db_path)
    
    # Override find_leads to only process 10 UHR cases for quick profiling
    original_find_leads = matcher.find_leads
    
    def find_leads_subset(min_score=0.35, limit=20):
        import sqlite3
        import json
        import re
        import math
        from collections import Counter
        from core.utils.geo_utils import haversine_distance, calculate_geo_score
        
        conn = sqlite3.connect(matcher.db_path)
        try:
            uhr_df, uhr_total = matcher.get_word_frequencies(conn, "unidentified_cases", "description")
            mp_df, mp_total = matcher.get_word_frequencies(conn, "missing_persons", "description")
            
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, case_number, estimated_sex, estimated_age_min, estimated_age_max, 
                       discovery_date, description, discovery_lat, discovery_lon, raw_data 
                FROM unidentified_cases 
                LIMIT 10
            """)
            uhr_cases = cursor.fetchall()
            
            all_leads = []
            for uhr in uhr_cases:
                u_id, u_num, u_sex, u_age_min, u_age_max, u_date, u_desc, u_lat, u_lon, u_raw_str = uhr
                u_raw = json.loads(u_raw_str) if u_raw_str else {}
                
                query = """
                    SELECT id, file_number, name, sex, age_at_disappearance, 
                           last_seen_date, description, last_seen_lat, last_seen_lon, raw_data 
                    FROM missing_persons 
                    WHERE (last_seen_date IS NULL OR last_seen_date <= ?)
                """
                params = [u_date if u_date else '9999-12-31']
                
                if u_sex and u_sex != 'Uncertain' and u_sex != 'Unknown':
                    query += " AND (sex IS NULL OR sex = 'Unknown' OR sex = 'Uncertain' OR sex = ?)"
                    params.append(u_sex)
                    
                cursor.execute(query, params)
                candidates = cursor.fetchall()
                
                for cand in candidates:
                    m_id, m_num, m_name, m_sex, m_age, m_date, m_desc, m_lat, m_lon, m_raw_str = cand
                    m_raw = json.loads(m_raw_str) if m_raw_str else {}
                    
                    if u_age_min and m_age and (m_age < u_age_min - 10 or (u_age_max and m_age > u_age_max + 10)):
                        continue
                    
                    text_score, features = matcher.score_text_overlap(u_desc, m_desc, uhr_df, mp_df, uhr_total, mp_total)
                    dist = haversine_distance(u_lat, u_lon, m_lat, m_lon)
                    geo_score = calculate_geo_score(dist)
                    pheno_score = matcher.calculate_phenotypic_score(u_raw, m_raw)
                    
                    composite_score = (text_score * 0.4) + (geo_score * 0.3) + (pheno_score * 0.3)
                    multiplier = matcher.calculate_bio_multiplier(u_raw, m_raw)
                    final_score = min(1.0, composite_score * multiplier)
                    
                    if final_score >= min_score:
                        all_leads.append({
                            "uhr_case": u_num,
                            "score": round(final_score, 3)
                        })
            return all_leads[:limit]
        finally:
            conn.close()

    pr = cProfile.Profile()
    pr.enable()
    find_leads_subset()
    pr.disable()
    
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('tottime')
    ps.print_stats(30)
    print(s.getvalue())

if __name__ == "__main__":
    profile_matcher()
