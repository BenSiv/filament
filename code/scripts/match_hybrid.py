
import os
import sys
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

# Adjust path to import from scripts directory if running from clean context
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    from match_cases import score_pair, normalize_sex, get_date
except ImportError:
    # If match_cases.py is in the same dir but not importable as module
    import importlib.util
    spec = importlib.util.spec_from_file_location("match_cases", os.path.join(current_dir, "match_cases.py"))
    match_cases = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(match_cases)
    score_pair = match_cases.score_pair
    normalize_sex = match_cases.normalize_sex
    get_date = match_cases.get_date

# Hybrid Matcher Configuration
DB_HOST = os.getenv('POSTGRES_HOST', 'localhost')
DB_PORT = os.getenv('POSTGRES_PORT', '5432')
DB_NAME = os.getenv('POSTGRES_DB', 'filament')
DB_USER = os.getenv('POSTGRES_USER', 'filament')
DB_PASS = os.getenv('POSTGRES_PASSWORD', 'filament_dev')

def get_db():
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASS
    )
    return conn

def calculate_hybrid_score(uhr_full, mp_full, vector_score, uhr_date_found):
    """
    Combine Vector Similarity with Standard Rule-Based Logic.
    """
    
    # 1. Use the shared scorer from match_cases
    # This handles Date checking, Age, Height, Features, Clothing, Tattoos
    # It returns None if a hard filter is failed (Age mismatch, Date mismatch, etc.)
    result = score_pair(uhr_full, mp_full, uhr_date_found)
    
    if result is None:
        return 0, ["Hard Filter Failed (Logic)"]
        
    rule_score, reasons = result
    
    if rule_score <= 0.1: # Allow low scores but penalize? No, 0 is bad.
        return 0, reasons 

    # 2. Composite
    # Vector score is "Semantic Overlap". Rule score is "Feature Validation".
    # Weighted average: High vector + High rule = Great match.
    final_score = (vector_score * 0.40) + (rule_score * 0.60)
    
    if vector_score > 0.6:
        reasons.insert(0, f"High Semantic Similarity ({vector_score:.2f})")
        
    return final_score, reasons

def main():
    print("Starting Hybrid RAG Matcher (Consolidated)...")
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # 1. Get UHR cases (embedding for search, raw_data for scoring)
    print("Fetching UHR cases...")
    cursor.execute("""
        SELECT case_number, discovery_date, estimated_sex, raw_data, embedding
        FROM unidentified_cases
        WHERE embedding IS NOT NULL
    """)
    uhr_cases = cursor.fetchall()
    print(f"Loaded {len(uhr_cases)} UHR cases.")
    
    matches = []
    
    print("Matching...")
    count = 0
    
    for uhr in uhr_cases:
        if count % 100 == 0:
            print(f"Processed {count}/{len(uhr_cases)}...")
        count += 1
        
        uhr_emb = uhr['embedding']
        uhr_raw = uhr['raw_data']
        uhr_sex = normalize_sex(uhr['estimated_sex'])
        uhr_date = get_date(uhr_raw, ['circumstances.dateFound']) # Use helper on raw
        
        # Build Query: KNN + Hard Filters (Sex)
        # Fetch raw_data for MPs to pass to score_pair
        
        sql = """
            SELECT file_number, name, raw_data,
                   1 - (embedding <=> %s::vector) as similarity
            FROM missing_persons
            WHERE embedding IS NOT NULL
        """
        params = [uhr_emb]
        
        # Strict Sex Filter (DB Side)
        if uhr_sex != 'U':
            target_sex = 'Female' if uhr_sex == 'F' else 'Male'
            sql += " AND (sex IS NULL OR sex = 'Unknown' OR sex = 'Uncertain' OR sex = %s)"
            params.append(target_sex)
            
        sql += " ORDER BY embedding <=> %s::vector LIMIT 20"
        params.append(uhr_emb)
        
        cursor.execute(sql, params)
        candidates = cursor.fetchall()
        
        for mp in candidates:
            mp_raw = mp['raw_data']
            vector_score = mp['similarity']
            
            # Extract Narratives for Story Line
            uhr_circ = uhr_raw.get('circumstances', {}).get('circumstancesOfRecovery', '')
            mp_circ = mp_raw.get('circumstances', {}).get('circumstancesOfDisappearance', '')
            
            # Narrative Density Filter (Pre-Score Check)
            # Require at least 20 chars of narrative or rich description
            def is_rich(c): return len(c) > 20
            
            if not is_rich(uhr_circ) and not is_rich(uhr_raw.get('description','')):
                 continue # Skip empty UHRs (or we can just penalize later, but user asked to prefilter)
            
            # Score using shared logic
            score, reasons = calculate_hybrid_score(uhr_raw, mp_raw, vector_score, uhr_date)
            
            # Boost score for Narrative Richness
            if is_rich(uhr_circ) and is_rich(mp_circ):
                score += 0.2
                reasons.append("Rich Narrative Context")
            
            if score > 0.70:
                matches.append({
                    'uhr_id': uhr['case_number'],
                    'mp_id': mp['file_number'],
                    'mp_name': mp['name'],
                    'score': round(float(score), 4),
                    'vector_score': round(float(vector_score), 4),
                    'reasons': reasons,
                    'narratives': {
                        'uhr': uhr_circ[:300] + "..." if len(uhr_circ) > 300 else uhr_circ,
                        'mp': mp_circ[:300] + "..." if len(mp_circ) > 300 else mp_circ
                    }
                })
                
    matches.sort(key=lambda x: x['score'], reverse=True)
    
    out_file = 'data/processed/leads_hybrid.json'
    with open(out_file, 'w') as f:
        json.dump(matches[:200], f, indent=2)
        
    print(f"Found {len(matches)} matches. Top 200 saved to {out_file}.")

if __name__ == "__main__":
    main()
