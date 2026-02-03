import json
import csv
import pandas as pd
import os

def flatten_dict(d, prefix=''):
    items = []
    for k, v in d.items():
        new_key = f"{prefix}{k}" if prefix else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key + '_').items())
        else:
            items.append((new_key, v))
    return dict(items)

def main():
    print("Loading data...")
    
    # Load Matches
    try:
        with open('data/processed/potential_matches.json', 'r') as f:
            matches_data = json.load(f)
    except FileNotFoundError:
        print("No matches file found.")
        return

    # Load Full MP Data for lookups
    try:
        with open('data/raw/rcmp_missing_persons.json', 'r') as f:
            mp_list = json.load(f)
            mp_dict = {m['case_id']: m for m in mp_list}
    except FileNotFoundError:
        print("No missing persons file found.")
        return

    rows = []
    
    print(f"Processing {len(matches_data)} travelers with matches...")
    
    for item in matches_data:
        t_id = item['traveler_id']
        mp_full = mp_dict.get(t_id, {})
        
        # Flatten MP data
        # Prefix with MP_ to distinguish
        mp_flat = flatten_dict(mp_full, prefix='MP_')
        
        for match in item['potential_matches']:
            score = match['score']
            reasons = "; ".join(match['reasons'])
            uhr_details = match.get('uhr_details', {})
            
            # Flatten UHR data
            # Prefix with UHR_
            uhr_flat = flatten_dict(uhr_details, prefix='UHR_')
            
            # Combine all
            row = {
                'Match_Score': score,
                'Match_Reasons': reasons,
                'Traveler_ID': t_id
            }
            row.update(mp_flat)
            row.update(uhr_flat)
            
            rows.append(row)
            
    if not rows:
        print("No matches to export.")
        return

    print(f"Generating CSV with {len(rows)} rows...")
    df = pd.DataFrame(rows)
    
    # Sort by Match Score Descending
    df = df.sort_values(by='Match_Score', ascending=False)
    
    # Reorder columns to have Score first, then ID, then MP cols, then UHR cols
    cols = list(df.columns)
    # Simple sort or prioritize specific ones
    pre_cols = ['Match_Score', 'Traveler_ID', 'Match_Reasons', 'MP_title', 'MP_case_id', 'MP_url', 'UHR_Case_Numbe', 'UHR_Date_Found']
    
    # Filter pre_cols that actually exist
    pre_cols = [c for c in pre_cols if c in cols]
    other_cols = [c for c in cols if c not in pre_cols]
    
    final_cols = pre_cols + other_cols
    df = df[final_cols]
    
    output_path = 'data/processed/matches_full.csv'
    df.to_csv(output_path, index=False)
    print(f"Successfully exported to {output_path}")

if __name__ == "__main__":
    main()
