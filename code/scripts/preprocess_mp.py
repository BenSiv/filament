import json
import os

INPUT_FILE = "data/raw/namus_missing.json"
OUTPUT_FILE = "data/raw/namus_missing_flat.json"

def main():
    print(f"Loading {INPUT_FILE}...")
    if not os.path.exists(INPUT_FILE):
        print("Input file not found!")
        return

    # Handle potentially massive file by reading line by line if it's JSONL, 
    # but here it's likely a JSON array. If it's too big, we might crash.
    # Given 200MB, it should fit in memory (process 1GB+).
    try:
        data = json.load(open(INPUT_FILE))
    except json.JSONDecodeError:
        print("Failed to parse JSON. Is it valid?")
        return

    flattened = []
    print(f"Processing {len(data)} records...")
    
    for case in data:
        # Extract features
        features = case.get('physicalFeatureDescriptions', [])
        clothing = case.get('clothingAndAccessoriesArticles', [])
        
        feature_text = ' '.join([f.get('description', '') for f in features]).lower()
        clothing_text = ' '.join([c.get('description', '') for c in clothing]).lower()
        
        # Extract specific string fields if they exist directly
        scars = case.get('scarsAndMarksDescription', '')
        tattoos = case.get('tattoosDescription', '')
        
        # Combine all physical descriptions
        full_feature_text = f"{feature_text} {scars} {tattoos}".strip()
        
        flat = {
            'idFormatted': case.get('idFormatted'),
            'namus2Number': case.get('namus2Number') or case.get('id'),
            'firstName': case.get('subjectIdentification', {}).get('firstName'),
            'lastName': case.get('subjectIdentification', {}).get('lastName'),
            'dateOfLastContact': case.get('dateOfLastContact'),
            'cityOfLastContact': case.get('cityOfLastContact'),
            'stateDisplayNameOfLastContact': case.get('stateDisplayNameOfLastContact') or case.get('state', {}).get('name'),
            'gender': case.get('gender', {}).get('name') if isinstance(case.get('gender'), dict) else case.get('gender'),
            'tattoos': full_feature_text,
            'clothing': clothing_text,
            # Age fields might be in different places (subjectIdentification usually)
            'computedMissingMinAge': case.get('subjectIdentification', {}).get('computedMissingMinAge') or case.get('computedMissingMinAge'),
            'computedMissingMaxAge': case.get('subjectIdentification', {}).get('computedMissingMaxAge') or case.get('computedMissingMaxAge'),
            # Height
            'heightFrom': case.get('subjectDescription', {}).get('heightFrom'),
            'heightTo': case.get('subjectDescription', {}).get('heightTo')
        }
        flattened.append(flat)

    print(f"Saving flattened data to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(flattened, f)
    
    print("Done.")

if __name__ == "__main__":
    main()
