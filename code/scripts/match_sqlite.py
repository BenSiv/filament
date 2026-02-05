
import sqlite3
import json
import re
import math
from collections import Counter
from datetime import datetime

DB_PATH = "data/filament.db"
OUTPUT_PATH = "data/processed/leads_advanced.json"

def get_connection():
    return sqlite3.connect(DB_PATH)

def get_word_frequencies(conn, table_name, column_name):
    """Calculate document frequency for words in descriptions to identify 'rare' identifiers."""
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

def calculate_specificity(word, df, total_docs):
    """
    Calculate an IDF-like score for a word. 
    Lower frequency = Higher specificity.
    """
    count = df.get(word, 0)
    if count == 0: return 2.0 # extremely rare or unknown
    return math.log10(total_docs / count)

def score_text_overlap(uhr_text, mp_text, uhr_df, mp_df, uhr_total, mp_total):
    """
    Score the overlap between two texts weighting by specificity.
    """
    if not uhr_text or not mp_text:
        return 0, []
        
    uhr_words = set(re.findall(r'\w+', uhr_text.lower()))
    mp_words = set(re.findall(r'\w+', mp_text.lower()))
    
    stop_words = {
        'the', 'and', 'was', 'with', 'found', 'on', 'in', 'at', 'of', 'for', 'to', 'is', 'has', 
        'unknown', 'unsure', 'uncertain', 'years', 'old', 'male', 'female', 'white', 'black', 
        'caucasian', 'american', 'african', 'hispanic', 'asian', 'native', 'race', 'sex', 
        'estimated', 'approximately', 'approx', 'about', 'inches', 'pounds', 'cm', 'kg', 'lbs',
        'body', 'description', 'subject', 'case', 'number', 'discovery', 'location', 'found',
        'sighting', 'last', 'seen', 'contact', 'date'
    }
    uhr_words -= stop_words
    mp_words -= stop_words
    
    common = uhr_words & mp_words
    if not common:
        return 0, []
        
    total_score = 0
    matched_features = []
    
    for word in common:
        # Average the specificity from both datasets if available
        spec1 = calculate_specificity(word, uhr_df, uhr_total)
        spec2 = calculate_specificity(word, mp_df, mp_total)
        specificity = (spec1 + spec2) / 2
        
        # Exponentially weight specificity to favor rare words
        # (e.g., 10^spec)
        weight = math.pow(10, specificity - 1.0) if specificity > 1.0 else specificity
        total_score += weight
        
        if specificity > 1.8: # Appear in less than ~1.5% of cases
            matched_features.append(f"{word} (Rare)")
        elif specificity > 1.2:
            matched_features.append(word)
            
    return min(1.0, total_score / 50), matched_features # Higher divisor for unique weights

def match_cases(conn):
    print("Pre-calculating specificity scores...")
    uhr_df, uhr_total = get_word_frequencies(conn, "unidentified_cases", "description")
    mp_df, mp_total = get_word_frequencies(conn, "missing_persons", "description")
    
    cursor = conn.cursor()
    
    # We'll pick a subset of UHR cases that have reasonably detailed descriptions to find "strong" leads
    cursor.execute("""
        SELECT id, case_number, estimated_sex, estimated_age_min, estimated_age_max, discovery_date, description, raw_data 
        FROM unidentified_cases 
        WHERE length(description) > 50
    """)
    uhr_cases = cursor.fetchall()
    
    all_leads = []
    print(f"Analyzing {len(uhr_cases)} UHR cases for leads...")
    
    for uhr in uhr_cases:
        u_id, u_num, u_sex, u_age_min, u_age_max, u_date, u_desc, u_raw = uhr
        
        # Candidate pruning in SQL (demographics + date)
        # MP must be missing BEFORE UHR found
        # Sex must match (if known)
        
        query = """
            SELECT id, file_number, name, sex, age_at_disappearance, last_seen_date, description, raw_data
            FROM missing_persons
            WHERE (last_seen_date IS NULL OR last_seen_date <= ?)
        """
        params = [u_date if u_date else '9999-12-31']
        
        if u_sex and u_sex != 'Uncertain':
            query += " AND (sex IS NULL OR sex = 'Unknown' OR sex = 'Uncertain' OR sex = ?)"
            params.append(u_sex)
            
        # We'll filter age in Python or further constrain SQL if needed
        cursor.execute(query, params)
        candidates = cursor.fetchall()
        
        for cand in candidates:
            m_id, m_num, m_name, m_sex, m_age, m_date, m_desc, m_raw = cand
            
            # Age filter (±20 years tolerance for discovery vs disappearance)
            if u_age_min and m_age:
                if abs(u_age_min - m_age) > 20: continue
            
            # Text matching with specificity
            text_score, features = score_text_overlap(u_desc, m_desc, uhr_df, mp_df, uhr_total, mp_total)
            
            if text_score > 0.4: # Significant overlap
                lead = {
                    "uhr_case": u_num,
                    "mp_file": m_num,
                    "mp_name": m_name,
                    "score": round(text_score, 3),
                    "shared_features": features,
                    "uhr_desc": u_desc[:200] + "...",
                    "mp_desc": m_desc[:200] + "..."
                }
                all_leads.append(lead)
                
        if len(all_leads) > 1000: break # Cap for demo/safety
        
    all_leads.sort(key=lambda x: x['score'], reverse=True)
    return all_leads

def main():
    conn = get_connection()
    try:
        leads = match_cases(conn)
        print(f"Found {len(leads)} potential leads.")
        
        import os
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        with open(OUTPUT_PATH, 'w') as f:
            json.dump(leads[:200], f, indent=2)
            
        print(f"Top 200 leads saved to {OUTPUT_PATH}")
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()
