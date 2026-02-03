
import os
import sys
import json
import random
import pickle
import numpy as np
import pandas as pd
import psycopg2
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from sentence_transformers import SentenceTransformer
from psycopg2.extras import RealDictCursor

# Config
DB_HOST = os.getenv('POSTGRES_HOST', 'localhost')
DB_PORT = os.getenv('POSTGRES_PORT', '5432')
DB_NAME = os.getenv('POSTGRES_DB', 'filament')
DB_USER = os.getenv('POSTGRES_USER', 'filament')
DB_PASS = os.getenv('POSTGRES_PASSWORD', 'filament_dev')
MODEL_NAME = 'all-MiniLM-L6-v2'
OUTPUT_MODEL = 'data/processed/match_classifier.pkl'

# Valid Feature Columns
FEATURES = ['vector_sim', 'days_diff', 'age_diff', 'keyword_overlap', 'same_sex']

def get_db():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASS
    )

def load_mps(conn):
    print("Loading MPs...")
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT file_number, last_seen_date, age_at_disappearance, sex, description, embedding FROM missing_persons WHERE embedding IS NOT NULL")
        return cur.fetchall()

def perturb_description(text):
    """
    Simulate decomposition/loss of info.
    - Remove random words
    - Keep some keywords
    """
    words = text.split()
    if len(words) < 5: return text
    
    # Keep 40-80% of words
    keep_ratio = random.uniform(0.4, 0.8)
    num_keep = int(len(words) * keep_ratio)
    
    # Random sample preserving order? Or just shuffle?
    # Decomp usually means chunks are missing.
    # Let's just pick random subset.
    kept = sorted(random.sample(range(len(words)), num_keep))
    new_words = [words[i] for i in kept]
    return " ".join(new_words)

def generate_synthetic_uhr(mp, model):
    """
    Create a fake UHR based on an MP.
    """
    uhr = mp.copy()
    
    # 1. Date Found = Last Seen + Random Delay (0 days to 10 years)
    if mp['last_seen_date']:
        delay = int(np.random.exponential(365 * 2)) # Avg 2 years
        uhr['discovery_date'] = mp['last_seen_date'] + timedelta(days=delay)
    else:
        uhr['discovery_date'] = None
        
    # 2. Age Check = MP Age + Error
    # UHR age is usually a range. We simulate the ESTIMATED age.
    # E.g. Actual 30 -> Estimated 25-35
    if mp['age_at_disappearance']:
        actual_age = mp['age_at_disappearance']
        error = random.randint(-5, 5)
        est_age = actual_age + error
        uhr['estimated_age_min'] = est_age - 5
        uhr['estimated_age_max'] = est_age + 5
    else:
        uhr['estimated_age_min'] = None
        uhr['estimated_age_max'] = None
        
    # 3. Description & Embedding
    # Perturb text and re-encode
    # NOTE: Re-encoding every time is slow. 
    # Optimization: Just add noise to the embedding vector directly?
    # Vector noise: geometric drift.
    # Cosine sim of 0.8-0.95 is typical for "Found" vs "Missing" descriptions.
    # We can simulate this by interpolating with a random vector.
    
    mp_vec = np.array(json.loads(mp['embedding']) if isinstance(mp['embedding'], str) else mp['embedding'])
    
    # Add noise to target cosine similarity ~0.85
    noise = np.random.normal(0, 0.15, mp_vec.shape)
    uhr_vec = mp_vec + noise
    # Normalize
    uhr_vec = uhr_vec / np.linalg.norm(uhr_vec)
    
    uhr['embedding'] = uhr_vec.tolist()
    
    # Description text (for keyword matching feature)
    uhr['description'] = perturb_description(mp['description'])
    
    return uhr

def extract_features(uhr, mp):
    """
    Calculate feature vector for a pair.
    """
    feats = {}
    
    # 1. Vector Similarity
    def parse_emb(e):
        return np.array(json.loads(e) if isinstance(e, str) else e)
        
    u_vec = parse_emb(uhr['embedding'])
    m_vec = parse_emb(mp['embedding'])
    
    # Cosine Sim
    feats['vector_sim'] = float(np.dot(u_vec, m_vec) / (np.linalg.norm(u_vec) * np.linalg.norm(m_vec)))
    
    # 2. Date Diff
    if uhr.get('discovery_date') and mp.get('last_seen_date'):
        diff = (uhr['discovery_date'] - mp['last_seen_date']).days
        feats['days_diff'] = diff
    else:
        feats['days_diff'] = 3650 # Default large gap
        
    # 3. Age Diff
    # If MP age is within UHR range -> 0 diff. Else distance.
    if mp['age_at_disappearance'] and uhr.get('estimated_age_min') and uhr.get('estimated_age_max'):
        m_age = mp['age_at_disappearance']
        u_min = uhr['estimated_age_min']
        u_max = uhr['estimated_age_max']
        
        if u_min <= m_age <= u_max:
            feats['age_diff'] = 0
        else:
            feats['age_diff'] = min(abs(m_age - u_min), abs(m_age - u_max))
    else:
        feats['age_diff'] = 10 # Default penalty
        
    # 4. Same Sex
    # 1 if match, 0 if not (or unknown)
    # Simplified for synthetic: assume data has M/F
    u_sex = uhr.get('sex') or uhr.get('estimated_sex')
    m_sex = mp.get('sex')
    feats['same_sex'] = 1 if u_sex == m_sex else 0
    
    # 5. Keyword Overlap (using sets)
    STOPWORDS = {'none', 'listed', 'unknown', 'male', 'female', 'white', 'caucasian', 'black', 'years', 'old'}
    def get_tokens(t):
        if not t: return set()
        return set(t.lower().split()) - STOPWORDS
        
    u_tok = get_tokens(uhr.get('description'))
    m_tok = get_tokens(mp.get('description'))
    feats['keyword_overlap'] = len(u_tok.intersection(m_tok))
    
    return [feats[col] for col in FEATURES]

def main():
    print("Starting Synthetic Training Pipeline...")
    
    conn = get_db()
    mps = load_mps(conn)
    conn.close()
    
    print(f"Loaded {len(mps)} base MPs.")
    
    X = []
    y = []
    
    # Generate Training Data
    # 5000 Positive Samples
    # 5000 Negative Samples
    
    target_count = min(len(mps), 5000)
    indices = range(len(mps))
    
    print(f"Generating {target_count} positive pairs...")
    
    # We need embedding model just for text checks if needed, 
    # but we are doing vector noise simulation.
    model = None # sentence_transformers not needed if we simulate vector noise
    
    for i in range(target_count):
        mp = mps[i]
        
        # Positive
        uhr_pos = generate_synthetic_uhr(mp, model)
        f_pos = extract_features(uhr_pos, mp)
        X.append(f_pos)
        y.append(1)
        
        # Negative (Random)
        rand_idx = random.choice(indices)
        if rand_idx == i: rand_idx = (i + 1) % len(mps)
        
        mp_rand = mps[rand_idx]
        
        # Treat mp_rand as UHR (just utilize its embedding/data)
        # We need to map MP fields to UHR fields for the extractor
        uhr_neg = {
            'discovery_date': mp_rand['last_seen_date'],
            'estimated_age_min': mp_rand['age_at_disappearance'] - 5 if mp_rand['age_at_disappearance'] else None,
            'estimated_age_max': mp_rand['age_at_disappearance'] + 5 if mp_rand['age_at_disappearance'] else None,
            'embedding': mp_rand['embedding'],
            'description': mp_rand['description'],
            'sex': mp_rand['sex']
        }
        
        f_neg = extract_features(uhr_neg, mp)
        X.append(f_neg)
        y.append(0)
        
        if i % 500 == 0:
            print(f"Generated {i*2} samples...")
            
    print("Training Model...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
    
    clf = RandomForestClassifier(n_estimators=100, max_depth=10)
    clf.fit(X_train, y_train)
    
    print("Evaluation:")
    y_pred = clf.predict(X_test)
    print(classification_report(y_test, y_pred))
    
    # Feature Importance
    print("\nFeature Importances:")
    for name, imp in zip(FEATURES, clf.feature_importances_):
        print(f"{name}: {imp:.4f}")
        
    # Save
    os.makedirs(os.path.dirname(OUTPUT_MODEL), exist_ok=True)
    with open(OUTPUT_MODEL, 'wb') as f:
        pickle.dump(clf, f)
        
    print(f"Model saved to {OUTPUT_MODEL}")

if __name__ == "__main__":
    main()
