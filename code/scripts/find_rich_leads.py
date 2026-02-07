
import json
import re

LEADS_FILE = "data/processed/leads.json"
UHR_FILE = "data/raw/namus_unidentified.json"
MP_FILE = "data/raw/namus_missing.json"

def load_data():
    print("Loading data")
    leads = json.load(open(LEADS_FILE))
    
    uhr_map = {}
    try:
        uhr_data = json.load(open(UHR_FILE))
        for u in uhr_data:
            uhr_map[u.get('idFormatted')] = u
    except: pass
    
    mp_map = {}
    try:
        mp_data = json.load(open(MP_FILE))
        print(f"Loaded {len(mp_data)} MPs")
        # Map by numeric ID and Formatted ID to be safe
        for m in mp_data:
            mp_map[str(m.get('namus2Number'))] = m
            mp_map[m.get('idFormatted')] = m
    except: pass
            
    return leads, mp_map, uhr_map

def get_text_content(obj):
    # Extract all text for richness analysis
    text = ""
    text += obj.get('circumstances', {}).get('circumstancesOfRecovery', '') or ""
    text += " " + (obj.get('circumstances', {}).get('circumstancesOfDisappearance', '') or "")
    
    for c in obj.get('clothingAndAccessoriesArticles', []):
        text += " " + (c.get('description', '') or "")
        
    for f in obj.get('physicalFeatureDescriptions', []):
        text += " " + (f.get('description', '') or "")
        
    return text.lower()

def main():
    leads, mp_map, uhr_map = load_data()
    
    rich_leads = []
    
    print(f"Scanning {len(leads)} leads for RICH matches")
    
    for lead in leads:
        uhr_id = lead['uhr_id']
        mp_id = lead['mp_id']
        
        # Resolve IDs
        uhr = uhr_map.get(uhr_id)
        
        # Handle MP ID formats
        cleaned_mp_id = mp_id.replace('MP', '')
        mp = mp_map.get(cleaned_mp_id) or mp_map.get(mp_id)
        
        if not uhr or not mp:
            continue
            
        # 0. TIMELINE CHECK
        uhr_found = uhr.get('circumstances', {}).get('dateFound')
        mp_missing = mp.get('sighting', {}).get('date') or mp.get('dateOfLastContact')
        
        if uhr_found and mp_missing:
            if mp_missing > uhr_found:
                continue

        # 1. STRICT RACE CHECK
        uhr_race = uhr.get('subjectDescription', {}).get('primaryEthnicity', {}).get('name', 'Unknown')
        mp_race = mp.get('subjectDescription', {}).get('ethnicities', [{}])[0].get('name', 'Unknown')
        
        # Skip if Race is defined and distinctly different
        if uhr_race != 'Unknown' and uhr_race != 'Uncertain' and mp_race != 'Unknown':
             if uhr_race != mp_race:
                 continue

        # 2. RARE WORD OVERLAP
        
        uhr_text = get_text_content(uhr)
        mp_text = get_text_content(mp)

        # Common English/Descriptive stopwords to ignore
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 
            'is', 'was', 'are', 'were', 'be', 'been', 'has', 'have', 'had', 'do', 'does', 'did',
            'he', 'she', 'it', 'they', 'his', 'her', 'its', 'their', 'him', 'them',
            'missing', 'unidentified', 'person', 'remains', 'found', 'seen', 'last', 'date',
            'wear', 'wearing', 'wore', 'description', 'subject', 'male', 'female', 'white', 'black',
            'left', 'right', 'upper', 'lower', 'side', 'front', 'back', 'top', 'bottom',
            'shirt', 'pants', 'shoes', 'socks', 'jacket', 'coat', 'hat', 'cap',
            'inch', 'cm', 'lbs', 'foot', 'feet', 'hair', 'eyes', 'brown', 'blue', 'green', 'short', 'long',
            'size', 'medium', 'large', 'small', 'color', 'colored', 'unknown', 'approximate', 'possible',
            'scar', 'tattoo', 'piercing', 'brand' # generic terms
        }
        
        uhr_tokens = set(re.findall(r'\w+', uhr_text)) - stopwords
        mp_tokens = set(re.findall(r'\w+', mp_text)) - stopwords
        
        # Filter purely numeric tokens
        uhr_tokens = {t for t in uhr_tokens if not t.isdigit()}
        mp_tokens = {t for t in mp_tokens if not t.isdigit()}
        
        common = uhr_tokens.intersection(mp_tokens)
        
        # Boost score heavily for count of unique intersecting words
        if len(common) >= 2:
             score = lead['score'] + (len(common) * 0.15)
             
             rich_leads.append({
                 'uhr_id': uhr_id,
                 'mp_id': mp_id,
                 'score': score,
                 'common': list(common),
                 'uhr_race': uhr_race,
                 'mp_race': mp_race,
                 'mp_name': f"{mp.get('subjectIdentification', {}).get('firstName')} {mp.get('subjectIdentification', {}).get('lastName')}"
             })

    # Sort
    rich_leads.sort(key=lambda x: x['score'], reverse=True)
    
    print("\nTop 15 RARE WORD Leads:")
    for l in rich_leads[:15]:
        print(f"{l['mp_name']} ({l['mp_id']}) <-> {l['uhr_id']}")
        print(f"  Score: {l['score']:.2f}")
        print(f"  Race: {l['mp_race']} / {l['uhr_race']}")
        print(f"  Overlaps: {l['common']}")
        print("---")

if __name__ == "__main__":
    main()
