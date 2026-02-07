
import json
import re
from datetime import datetime
import argparse

UHR_FILE = 'data/raw/bc_uhr_cases.json'
MISSING_RCMP = 'data/raw/rcmp_missing_persons.json'
MISSING_CHARLEY = 'data/raw/charley_washington.json'
OUTPUT_FILE = 'data/processed/potential_matches.json'

TRAVELER_KEYWORDS = [
    'tourist', 'visitor', 'vacation', 'traveling', 'travelling', 
    'hitchhiking', 'abroad', 'flight', 'airport', 'foreign', 
    'national of', 'citizen of', 'backpacking', 'camping', 'sightseeing'
]

def load_json(path):
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"File not found: {path}")
        return []

import pgeocode
import numpy as np

import json
import time
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

# Initialize geocoder
geolocator = Nominatim(user_agent="filament_missing_persons_project")

# Simple in-memory cache to avoid redundant API calls and respect rate limits
GEO_CACHE = {}

def get_location_coords(text):
    """
    Extracts city name from text and returns (lat, lon).
    Uses geopy for lookup with caching.
    """
    if not text:
        return None, None
        
    if not text:
        return None, None
    
    query = text
    # Extract "Missing from X" if present in narrative
    if "Missing from" in text:
        import re
        match = re.search(r"Missing from\s+(.*?)(?=\s+Missing|\s+Personal|\n|$)", text)
        if match:
             query = match.group(1).strip()
    
    # Heuristic cleanup
    if "," in query:
        parts = query.split(",")
        if len(parts) >= 2:
             query = f"{parts[0].strip()}, {parts[1].strip()}"
        else:
             query = parts[0].strip()
    
    query = query.strip()
    if len(query) > 50 or len(query) < 3: 
        return None, None
    
    # Avoid geocoding descriptive text that isn't a city
    if "Reference" in query or "Case" in query: 
        return None, None

    if query in GEO_CACHE:
        return GEO_CACHE[query], query
        
    try:
        # Rate limiting
        time.sleep(0.5) 
        location = geolocator.geocode(query + ", Canada", timeout=2)
        if location:
            coords = (location.latitude, location.longitude)
            GEO_CACHE[query] = coords
            return coords, query
        else:
            # Cache failure to prevent retry
            GEO_CACHE[query] = None
    except Exception as e:
        print(f"Geocoding error for {query}: {e}")
        GEO_CACHE[query] = None # Cache error as failure
        
    return None, None

def extract_date(text):
    # Try to find "Date last seen: YYYY-MM-DD" or similar patterns
    # This is a best-effort regex
    patterns = [
        r"Date last seen\s*:\s*(\d{4}-\d{2}-\d{2})",
        r"Date last seen\s*:\s*(\w+ \d{1,2}, \d{4})",
        r"Missing Since\s*:\s*(\w+ \d{1,2}, \d{4})"
    ]
    
    for pat in patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            date_str = match.group(1)
            # Try parsing various formats
            settings = ['%Y-%m-%d', '%B %d, %Y', '%b %d, %Y']
            for fmt in settings:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
    # Remove ordinal suffixes st, nd, rd, th to simplify parsing
    # e.g. "August 26th, 1986" -> "August 26, 1986"
    clean_text = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', text)
    
    patterns = [
        r"Date last seen\s*:\s*(\d{4}-\d{2}-\d{2})",
        r"Date last seen\s*:\s*(\w+ \d{1,2}, \d{4})",
        r"Missing Since\s*:\s*(\w+ \d{1,2}, \d{4})",
        r"Missing since\s*(\w+ \d{1,2}, \d{4})",
        # Loose patterns for narratives
        r"(?:last seen|missing) on (\w+ \d{1,2}, \d{4})",
        r"(?:last seen|missing).*?(\w+ \d{1,2}, \d{4})"
    ]
    
    for pat in patterns:
        match = re.search(pat, clean_text, re.IGNORECASE)
        if match:
            date_str = match.group(1)
            settings = ['%Y-%m-%d', '%B %d, %Y', '%b %d, %Y']
            for fmt in settings:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
    return None

import spacy
nlp = spacy.load("en_core_web_sm")

def extract_features_nlp(text):
    if not text: return {'tattoos': [], 'clothing': [], 'scars': []}
    doc = nlp(text.lower())
    features = {
        'tattoos': [],
        'clothing': [],
        'scars': []
    }
    
    # Keywords indicating category
    tattoo_heads = ['tattoo', 'ink', 'design', 'rose', 'dragon']
    clothing_heads = ['shirt', 'jacket', 'pants', 'jeans', 'shoe', 'boot', 'coat', 'sweater', 'hat', 'cap', 'sneaker', 'hoodie', 'top', 'bottom']
    scar_heads = ['scar', 'mark', 'birthmark']
    
    for chunk in doc.noun_chunks:
        head = chunk.root.lemma_
        if head in tattoo_heads:
            features['tattoos'].append(chunk.text)
        elif head in clothing_heads:
            features['clothing'].append(chunk.text)
        elif head in scar_heads:
            features['scars'].append(chunk.text)
            
    return features

def parse_pmi_days(pmi_str):
    if not pmi_str: return 0
    pmi_str = str(pmi_str).lower().strip()
    if pmi_str == "nan" or not pmi_str: return 0
    
    # Simple regex for quantity and unit
    # "2 months", "1 year", "years" (implied 1?), "14 days"
    try:
        parts = pmi_str.split()
        if not parts: return 0
        
        val = 0
        unit = ""
        
        # specific handling for "a few days" etc?
        # heuristic: take first number found
        import re
        nums = re.findall(r'\d+', pmi_str)
        if nums:
            val = int(nums[0])
        else:
            # Maybe "one month", "year"
             if "one" in pmi_str or re.match(r'^(year|month|week|day)', pmi_str):
                 val = 1
        
        if val == 0: return 0
        
        if "year" in pmi_str:
            return val * 365
        elif "month" in pmi_str:
            return val * 30
        elif "week" in pmi_str:
            return val * 7
        elif "day" in pmi_str:
            return val
            
        return 0
    except:
        return 0

def get_mp_age(mp):
    # Try explicit field
    details = mp.get('details', {})
    
    # RCMP format
    if 'Age at disappearance' in details:
        try:
            return int(details['Age at disappearance'])
        except:
            pass
            
    # Charley format ("Age: 52 years old")
    if 'Age' in details:
        try:
            # Extract first number
            import re
            m = re.search(r'\d+', str(details['Age']))
            if m:
                return int(m.group(0))
        except:
            pass
            
    return None

def parse_height_cm(h_str):
    if not h_str: return None
    h_str = str(h_str).strip().lower()
    if h_str == "nan" or not h_str: return None
    
    # Try cm match first (e.g. "182cm")
    import re
    cm_match = re.search(r'(\d+)\s*cm', h_str)
    if cm_match:
        return int(cm_match.group(1))
        
    # Try ft/in match (e.g. "5 ft 10", "5'10")
    ft_match = re.search(r'(\d+)\s*(?:ft|\')\s*(\d+)?', h_str)
    if ft_match:
        ft = int(ft_match.group(1))
        inch = int(ft_match.group(2)) if ft_match.group(2) else 0
        return int((ft * 30.48) + (inch * 2.54))
        
    return None

def get_mp_height(mp):
    details = mp.get('details', {})
    
    # RCMP Format
    if 'Height' in details:
        return parse_height_cm(details['Height'])
        
    # Charley Format ("Height and Weight: 5'10, 170 pounds")
    if 'Height and Weight' in details:
        # Pass the whole string, parse_height_cm needs update/verify it handles extra text
        # Clean it up first: take first part before comma
        h_str = details['Height and Weight'].split(',')[0]
        return parse_height_cm(h_str)
        
    return None

def is_traveler(narrative):
    narrative_lower = narrative.lower()
    matches = [kw for kw in TRAVELER_KEYWORDS if kw in narrative_lower]
    return len(matches) > 0, matches

def main():
    print("Loading data")
    uhr_data = load_json(UHR_FILE)
    if isinstance(uhr_data, dict) and 'features' in uhr_data:
        uhr_cases = [f['attributes'] for f in uhr_data['features']]
    else:
        uhr_cases = uhr_data # Assuming list if not geojson
        
    # Load and combine sources
    missing_persons = []
    
    # RCMP
    rcmp = load_json(MISSING_RCMP)
    for m in rcmp:
        m['source'] = 'RCMP'
        missing_persons.append(m)
        
    # Charley
    charley = load_json(MISSING_CHARLEY)
    for m in charley:
        m['source'] = 'Charley'
        # Normalize title/name for consistency with downstream code using 'title'
        if 'name' in m and 'title' not in m:
             m['title'] = m['name'] 
        if 'url' in m and 'case_id' not in m:
             m['case_id'] = m['url'] # Use URL as ID for Charley
        missing_persons.append(m)
    
    print(f"Loaded {len(uhr_cases)} UHR cases and {len(missing_persons)} Missing Persons cases.")
    
    travelers = []
    for mp in missing_persons:
        is_trav, keywords = is_traveler(mp.get('narrative', ''))
        
        # Always include Charley Project cases (WA) as they are cross-border candidates by definition
        if mp.get('source') == 'Charley':
            is_trav = True
            keywords.append('cross-border')
            
        if is_trav:
            mp['traveler_keywords'] = keywords
            mp['traveler_keywords'] = keywords
            
            # Combine narrative and explicit date field for extraction
            # Try explicit field first
            d_text = mp.get('narrative', '')
            if 'details' in mp and isinstance(mp['details'], dict):
                 if 'Missing since' in mp['details']:
                      d_text += f"\nMissing since: {mp['details']['Missing since']}"
            
            date_last_seen = extract_date(d_text)
            mp['date_last_seen_dt'] = date_last_seen
            # Extract NLP features
            mp['nlp_features'] = extract_features_nlp(mp.get('narrative', ''))
            
            travelers.append(mp)
            
    print(f"Identified {len(travelers)} potential travelers.")
    
    matches = []

    # Pre-calculate haversine function for speed
    from math import radians, cos, sin, asin, sqrt
    def fast_haversine(lat1, lon1, lat2, lon2):
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlon = lon2 - lon1 
        dlat = lat2 - lat1 
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a)) 
        r = 6371 
        return c * r

    for t in travelers:
        t_matches = []
        t_sex = "Male" if "Male" in t.get('narrative','') else "Female" if "Female" in t.get('narrative','') else "Unknown"
        
        # Simple extraction of sex from narrative if not explicit field
        # Ideally scaper should parse this.
        
        t_date = t.get('date_last_seen_dt')
        
        for u in uhr_cases:
            # 1. Sex Check
            u_sex = u.get('Sex')
            if u_sex and t_sex != "Unknown" and u_sex != t_sex:
                continue
                
            # 2. Date Check & PMI Check
            u_date_epoch = u.get('Date_Found')
            if u_date_epoch and t_date:
                u_dt = datetime.fromtimestamp(u_date_epoch / 1000)
                if u_dt < t_date:
                    continue # Found before they went missing (Impossible)
                
                # PMI Check (Post Mortem Interval)
                # Time Missing (days) must be >= PMI Min (days) roughly
                time_missing_days = (u_dt - t_date).days
                pmi_min_str = u.get('PMI_Min')
                pmi_min_days = parse_pmi_days(pmi_min_str)
                
                # Check if body is "older" than the missing time
                # converting to days. If PMI is 1 year (365 days) and missing 10 days -> Impossible.
                # Allow small buffer (e.g. 10%)
                if pmi_min_days > 0 and time_missing_days < (pmi_min_days * 0.9):
                    continue # Body is too decomposed for this recent missing person
            
            # 3. Age Check
            t_age = get_mp_age(t)
            u_min_age = u.get('Minimum_Ag')
            u_max_age = u.get('Maximum_Ag')

            if t_age is not None and u_min_age and u_max_age:
                # Type conversion safety
                try:
                    u_min = int(u_min_age)
                    u_max = int(u_max_age)
                    # Allow 5 year buffer? 
                    # If mp_age is 20, and u_range is 40-50, unlikely.
                    if t_age < (u_min - 5) or t_age > (u_max + 5):
                        continue
                except:
                    pass
            
            # 4. Height Check (Filter or Score?)
            # User wants high score for height. Let's filter extreme mismatches and score good ones.
            t_height = get_mp_height(t)
            u_min_h_str = u.get('Minimum_He')
            u_max_h_str = u.get('Maximum_He')
            
            u_h_min = parse_height_cm(u_min_h_str)
            u_h_max = parse_height_cm(u_max_h_str)
            
            if t_height and u_h_min and u_h_max:
                # Tolerance of 5cm (approx 2 inches) outside range
                if t_height < (u_h_min - 5) or t_height > (u_h_max + 5):
                     # Discrepancy > 2 inches, penalize or skip?
                     # Let's Skip to be strict as per user feedback "3 inches is daming"
                     continue

            # 5. Geo Check
            distance_km = None
            # Geocoding disabled due to rate limits
            # if u.get('Latitude') and u.get('Longitude'): ...
            
            # 4. Descriptives Check (NLP)
            desc_score = 0
            desc_notes = []
            
            # Use pre-extracted features
            t_features = t.get('nlp_features', {'tattoos':[], 'clothing':[]})
            
            u_tattoos = str(u.get('Tattoos', '')).lower()
            if u_tattoos and u_tattoos != "nan":
                 for feat in t_features['tattoos']:
                      # Check if the tattoo feature words appear in UHR tattoo description
                      feat_tokens = [w for w in feat.split() if w not in ['tattoo']]
                      if any(w in u_tattoos for w in feat_tokens if len(w)>3):
                           desc_score += 5
                           desc_notes.append(f"Tattoo match: {feat}")
            
            u_clothing = str(u.get('Clothing', '')).lower()
            if u_clothing and u_clothing != "nan":
                 for feat in t_features['clothing']:
                      feat_tokens = [w for w in feat.split() if len(w)>3]
                      if any(w in u_clothing for w in feat_tokens):
                           desc_score += 3
                           desc_notes.append(f"Clothing match: {feat}")
                           
            # Fallback to simple keyword match if NLP missed something (optional, but let's trust NLP for now to reduce noise)

            score = 0
            reasons = []
            
            # Start with base score for date validation
            if u_date_epoch and t_date:
                score += 10
                reasons.append("Timeline possible")
                
                # PMI consistency score
                # If Time Missing is within PMI Window?
                # PMI Max?
                pmi_max_str = u.get('PMI_Max')
                pmi_max_days = parse_pmi_days(pmi_max_str)
                
                time_missing_days = (u_dt - t_date).days
                
                # If fits nicely in PMI window
                if pmi_min_days > 0 and pmi_max_days > 0:
                    if pmi_min_days <= time_missing_days <= pmi_max_days:
                         score += 15
                         reasons.append(f"Matches PMI ({pmi_min_str}-{pmi_max_str})")
                
                # Replace simple "< 1 year" bonus with logic
                # Only bonus closeness if PMI is small?
                # Or just report valid timeline logic.
                if time_missing_days < 365:
                     # Only helpful if pmi allows it.
                     if pmi_min_days < 365:
                         score += 5
                         reasons.append(f"Recent missing ({time_missing_days} days)")
            
            if t_height and u_h_min and u_h_max:
                # If strictly within range
                if u_h_min <= t_height <= u_h_max:
                     score += 20
                     reasons.append(f"Height match ({t_height}cm inside {u_h_min}-{u_h_max})")
                elif (u_h_min - 3) <= t_height <= (u_h_max + 3):
                     score += 10
                     reasons.append(f"Height close ({t_height}cm near {u_h_min}-{u_h_max})")

            if distance_km is not None:
                if distance_km < 50:
                    score += 20
                    reasons.append(f"Close proximity (~{int(distance_km)}km from {t_city})")
                elif distance_km < 200:
                    score += 5
                    reasons.append(f"Regional proximity (~{int(distance_km)}km from {t_city})")
            
            score += desc_score
            reasons.extend(desc_notes)
            
            t_matches.append({
                "uhr_case": u.get('Case_Numbe'),
                "score": score,
                "reasons": reasons,
                "uhr_details": u,
                "distance_km": distance_km
            })
        
        # Sort matches by score
        t_matches.sort(key=lambda x: x['score'], reverse=True)
        if t_matches:
            matches.append({
                "traveler": t['title'],
                "traveler_id": t['case_id'],
                "missing_date": str(t_date),
                "potential_matches": t_matches[:5] # Top 5
            })

    # Output Report
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(matches, f, indent=2)
        
    print(f"\nFound {len(matches)} travelers with potential matches.")
    for m in matches[:3]:
        print(f"\nTraveler: {m['traveler']} (Missing: {m['missing_date']})")
        for pm in m['potential_matches']:
            print(f"  -> UHR Case: {pm['uhr_case']} (Score: {pm['score']}) - {pm['uhr_details'].get('Town_City')}")

if __name__ == "__main__":
    main()
