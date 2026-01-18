#!/usr/bin/env python3
"""
Cross-Reference Matching System (Smart Filtering)

ALGORITHMIC OPTIMIZATIONS:
1. State-based indexing: Only compare UHR in state X with MPs from nearby states
2. Date filtering: Only compare MPs who went missing BEFORE UHR was found  
3. Sex filtering: Only compare same sex
4. Age binning: Skip if age ranges can't possibly overlap

This reduces 450M comparisons to ~5-10M (95%+ reduction).
"""

import json
import argparse
import os
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2
from collections import defaultdict

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    def tqdm(iterable, **kwargs):
        total = kwargs.get('total', '?')
        desc = kwargs.get('desc', 'Processing')
        for i, item in enumerate(iterable):
            if (i + 1) % 500 == 0:
                print(f"  {desc}: {i+1}/{total}")
            yield item

DATA_DIR = "data/raw"
OUTPUT_DIR = "data/processed"

# State adjacency for nearby matching (simplified - US states)
NEARBY_STATES = {
    'AL': ['FL', 'GA', 'MS', 'TN'], 'AK': [], 'AZ': ['CA', 'NM', 'NV', 'UT'],
    'AR': ['LA', 'MO', 'MS', 'OK', 'TN', 'TX'], 'CA': ['AZ', 'NV', 'OR'],
    'CO': ['AZ', 'KS', 'NE', 'NM', 'OK', 'UT', 'WY'], 'CT': ['MA', 'NY', 'RI'],
    'DE': ['MD', 'NJ', 'PA'], 'FL': ['AL', 'GA'], 'GA': ['AL', 'FL', 'NC', 'SC', 'TN'],
    'HI': [], 'ID': ['MT', 'NV', 'OR', 'UT', 'WA', 'WY'], 'IL': ['IN', 'IA', 'KY', 'MO', 'WI'],
    'IN': ['IL', 'KY', 'MI', 'OH'], 'IA': ['IL', 'MN', 'MO', 'NE', 'SD', 'WI'],
    'KS': ['CO', 'MO', 'NE', 'OK'], 'KY': ['IL', 'IN', 'MO', 'OH', 'TN', 'VA', 'WV'],
    'LA': ['AR', 'MS', 'TX'], 'ME': ['NH'], 'MD': ['DE', 'PA', 'VA', 'WV', 'DC'],
    'MA': ['CT', 'NH', 'NY', 'RI', 'VT'], 'MI': ['IN', 'OH', 'WI'],
    'MN': ['IA', 'ND', 'SD', 'WI'], 'MS': ['AL', 'AR', 'LA', 'TN'],
    'MO': ['AR', 'IL', 'IA', 'KS', 'KY', 'NE', 'OK', 'TN'],
    'MT': ['ID', 'ND', 'SD', 'WY'], 'NE': ['CO', 'IA', 'KS', 'MO', 'SD', 'WY'],
    'NV': ['AZ', 'CA', 'ID', 'OR', 'UT'], 'NH': ['MA', 'ME', 'VT'],
    'NJ': ['DE', 'NY', 'PA'], 'NM': ['AZ', 'CO', 'OK', 'TX', 'UT'],
    'NY': ['CT', 'MA', 'NJ', 'PA', 'VT'], 'NC': ['GA', 'SC', 'TN', 'VA'],
    'ND': ['MN', 'MT', 'SD'], 'OH': ['IN', 'KY', 'MI', 'PA', 'WV'],
    'OK': ['AR', 'CO', 'KS', 'MO', 'NM', 'TX'], 'OR': ['CA', 'ID', 'NV', 'WA'],
    'PA': ['DE', 'MD', 'NJ', 'NY', 'OH', 'WV'], 'RI': ['CT', 'MA'],
    'SC': ['GA', 'NC'], 'SD': ['IA', 'MN', 'MT', 'ND', 'NE', 'WY'],
    'TN': ['AL', 'AR', 'GA', 'KY', 'MO', 'MS', 'NC', 'VA'],
    'TX': ['AR', 'LA', 'NM', 'OK'], 'UT': ['AZ', 'CO', 'ID', 'NV', 'NM', 'WY'],
    'VT': ['MA', 'NH', 'NY'], 'VA': ['KY', 'MD', 'NC', 'TN', 'WV', 'DC'],
    'WA': ['ID', 'OR'], 'WV': ['KY', 'MD', 'OH', 'PA', 'VA'],
    'WI': ['IA', 'IL', 'MI', 'MN'], 'WY': ['CO', 'ID', 'MT', 'NE', 'SD', 'UT'],
    'DC': ['MD', 'VA'],
    # Canada
    'BC': ['WA', 'ID', 'MT', 'AB'], 'AB': ['BC', 'SK', 'MT'],
    'ON': ['MI', 'MN', 'NY'], 'QC': ['NY', 'VT', 'ME', 'NH'],
}


def load_json(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, 'r') as f:
        try:
            return json.loads(f.read().strip())
        except:
            return []


def normalize_sex(v):
    if not v: return "U"
    v = str(v).lower()
    if v[0] == 'm': return "M"
    if v[0] == 'f': return "F"
    return "U"


def get_state(case):
    """Extract 2-letter state code."""
    # Complete US state mapping
    STATE_MAP = {
        'ALABAMA': 'AL', 'ALASKA': 'AK', 'ARIZONA': 'AZ', 'ARKANSAS': 'AR',
        'CALIFORNIA': 'CA', 'COLORADO': 'CO', 'CONNECTICUT': 'CT', 'DELAWARE': 'DE',
        'FLORIDA': 'FL', 'GEORGIA': 'GA', 'HAWAII': 'HI', 'IDAHO': 'ID',
        'ILLINOIS': 'IL', 'INDIANA': 'IN', 'IOWA': 'IA', 'KANSAS': 'KS',
        'KENTUCKY': 'KY', 'LOUISIANA': 'LA', 'MAINE': 'ME', 'MARYLAND': 'MD',
        'MASSACHUSETTS': 'MA', 'MICHIGAN': 'MI', 'MINNESOTA': 'MN', 'MISSISSIPPI': 'MS',
        'MISSOURI': 'MO', 'MONTANA': 'MT', 'NEBRASKA': 'NE', 'NEVADA': 'NV',
        'NEW HAMPSHIRE': 'NH', 'NEW JERSEY': 'NJ', 'NEW MEXICO': 'NM', 'NEW YORK': 'NY',
        'NORTH CAROLINA': 'NC', 'NORTH DAKOTA': 'ND', 'OHIO': 'OH', 'OKLAHOMA': 'OK',
        'OREGON': 'OR', 'PENNSYLVANIA': 'PA', 'RHODE ISLAND': 'RI', 'SOUTH CAROLINA': 'SC',
        'SOUTH DAKOTA': 'SD', 'TENNESSEE': 'TN', 'TEXAS': 'TX', 'UTAH': 'UT',
        'VERMONT': 'VT', 'VIRGINIA': 'VA', 'WASHINGTON': 'WA', 'WEST VIRGINIA': 'WV',
        'WISCONSIN': 'WI', 'WYOMING': 'WY', 'DISTRICT OF COLUMBIA': 'DC',
        'PUERTO RICO': 'PR', 'GUAM': 'GU', 'VIRGIN ISLANDS': 'VI',
        'BRITISH COLUMBIA': 'BC', 'ONTARIO': 'ON', 'ALBERTA': 'AB', 'QUEBEC': 'QC'
    }
    
    for field in ['stateDisplayNameOfRecovery', 'stateOfRecovery', 
                  'stateDisplayNameOfLastContact', 'stateOfLastContact', 'state']:
        val = case.get(field)
        if val:
            val = str(val).strip().upper()
            if len(val) == 2:
                return val
            if val in STATE_MAP:
                return STATE_MAP[val]
    return None


def get_year(case, field_names):
    """Extract year from date fields."""
    for field in field_names:
        val = case.get(field)
        if val and isinstance(val, str):
            try:
                return int(val.split('T')[0].split('-')[0])
            except:
                pass
    return None


def parse_date(date_str):
    """Parse date string to comparable tuple (year, month, day)."""
    if not date_str:
        return None
    try:
        parts = date_str.split('T')[0].split('-')
        return (int(parts[0]), int(parts[1]), int(parts[2]))
    except:
        return None


def get_date(case, field_names):
    """Get date tuple from case."""
    for field in field_names:
        val = case.get(field)
        if val:
            result = parse_date(val)
            if result:
                return result
    return None


def get_age_range(case, is_uhr=True):
    """Get age range as (min, max)."""
    if is_uhr:
        fields = [('estimatedAgeFrom', 'estimatedAgeTo'), ('computedMissingMinAge', 'computedMissingMaxAge')]
    else:
        fields = [('computedMissingMinAge', 'computedMissingMaxAge')]
    
    for min_f, max_f in fields:
        try:
            age_min = int(case.get(min_f))
            age_max = int(case.get(max_f))
            return (age_min, age_max)
        except:
            pass
    return (0, 100)  # Unknown = wide range


def get_height_cm(case):
    """
    Extract height in cm. Returns (min_cm, max_cm) or (None, None).
    Handles various formats: cm, inches, feet+inches.
    """
    # Try different field names
    for field in ['heightFrom', 'heightTo', 'height', 'Height', 
                  'heightFromClassic', 'heightToClassic',
                  'estimatedHeightFrom', 'estimatedHeightTo']:
        val = case.get(field)
        if val:
            try:
                # If numeric, assume cm
                cm = float(val)
                if cm < 100:  # Likely feet
                    cm = cm * 30.48
                elif cm < 250:  # Reasonable cm
                    return cm
            except:
                pass
            
            # Try parsing string like "5'10" or "170 cm"
            if isinstance(val, str):
                val = val.lower().strip()
                if 'cm' in val:
                    try:
                        return float(val.replace('cm', '').strip())
                    except:
                        pass
                if "'" in val or 'ft' in val:
                    try:
                        parts = val.replace('ft', "'").replace('"', '').split("'")
                        feet = int(parts[0])
                        inches = int(parts[1]) if len(parts) > 1 and parts[1] else 0
                        return feet * 30.48 + inches * 2.54
                    except:
                        pass
    return None


def get_height_range(case, is_uhr=True):
    """Get height range in cm as (min, max). NamUs uses inches in subjectDescription."""
    # Try nested subjectDescription first (full case details)
    sd = case.get('subjectDescription', {})
    h_from = sd.get('heightFrom')
    h_to = sd.get('heightTo')
    
    # Also try top-level fields (summaries or other formats)
    if not h_from:
        h_from = case.get('heightFrom') or case.get('estimatedHeightFrom')
    if not h_to:
        h_to = case.get('heightTo') or case.get('estimatedHeightTo')
    
    # Convert inches to cm (NamUs uses inches)
    def to_cm(val):
        if val is None:
            return None
        try:
            inches = float(val)
            if inches < 100:  # Definitely inches
                return inches * 2.54
            return inches  # Already cm
        except:
            return None
    
    h_min_cm = to_cm(h_from)
    h_max_cm = to_cm(h_to)
    
    if h_min_cm and h_max_cm:
        return (min(h_min_cm, h_max_cm), max(h_min_cm, h_max_cm))
    elif h_min_cm:
        return (h_min_cm - 5, h_min_cm + 5)
    elif h_max_cm:
        return (h_max_cm - 5, h_max_cm + 5)
    return (None, None)


def build_mp_index(mp_cases):
    """Build multi-dimensional index for fast lookup."""
    print("Building MP index (sex × state × decade)...")
    
    # Index structure: sex -> state -> list of MPs
    index = defaultdict(lambda: defaultdict(list))
    
    for mp in mp_cases:
        sex = normalize_sex(mp.get('gender') or mp.get('sex') or mp.get('details', {}).get('Gender'))
        state = get_state(mp)
        
        index[sex][state].append(mp)
        index[sex][None].append(mp)  # Also add to "any state" bucket
    
    # Stats
    total = sum(len(v) for states in index.values() for v in states.values())
    print(f"  Indexed {len(mp_cases)} MPs into {len(index)} sex buckets")
    
    return index


def get_candidate_mps(mp_index, uhr_sex, uhr_state):
    """Get candidate MPs for a UHR based on sex and nearby states."""
    candidates = []
    
    # Same sex candidates
    sex_bucket = mp_index.get(uhr_sex, {})
    
    if uhr_state:
        # Get MPs from same state
        candidates.extend(sex_bucket.get(uhr_state, []))
        
        # Get MPs from neighboring states
        for nearby in NEARBY_STATES.get(uhr_state, []):
            candidates.extend(sex_bucket.get(nearby, []))
    else:
        # Unknown state - use all
        candidates = sex_bucket.get(None, [])
    
    # Also include unknown-sex MPs
    unknown_bucket = mp_index.get('U', {})
    if uhr_state:
        candidates.extend(unknown_bucket.get(uhr_state, []))
        for nearby in NEARBY_STATES.get(uhr_state, []):
            candidates.extend(unknown_bucket.get(nearby, []))
    else:
        candidates.extend(unknown_bucket.get(None, []))
    
    return candidates


def score_pair(uhr, mp, uhr_date):
    """Score a candidate pair. Returns (score, reasons) or None."""
    reasons = []
    
    # Date filter: MP must be missing BEFORE UHR found (full date comparison)
    mp_date = get_date(mp, ['dateOfLastContact', 'dateMissing'])
    if mp_date and uhr_date and mp_date > uhr_date:
        return None  # MP went missing AFTER remains were found - impossible
    
    # Age filter
    uhr_age = get_age_range(uhr, True)
    mp_age = get_age_range(mp, False)
    
    # Check overlap with tolerance
    if uhr_age[1] < mp_age[0] - 10 or uhr_age[0] > mp_age[1] + 15:
        return None
    
    # Add sex match info
    uhr_sex = uhr.get('sex', 'Unknown')
    mp_sex = mp.get('gender', 'Unknown')
    reasons.append(f"Sex match: {uhr_sex}")
    
    # Add age info
    if uhr_age[0] and uhr_age[1] and mp_age[0]:
        reasons.append(f"Age: UHR {uhr_age[0]}-{uhr_age[1]}, MP ~{mp_age[0]}")
    
    # Height filter (±15cm tolerance)
    uhr_height = get_height_range(uhr, True)
    mp_height = get_height_range(mp, False)
    height_score = 0.5  # Default neutral
    
    if uhr_height[0] and mp_height[0]:
        # Both have height data - check overlap
        tolerance = 15  # cm
        if uhr_height[1] + tolerance < mp_height[0] or uhr_height[0] - tolerance > mp_height[1]:
            return None  # Heights don't overlap
        
        # Calculate height match score
        overlap = min(uhr_height[1], mp_height[1]) - max(uhr_height[0], mp_height[0])
        height_score = min(1.0, max(0.3, overlap / 20))
        reasons.append("Height match")
    
    # Calculate score components
    age_overlap = min(uhr_age[1], mp_age[1]) - max(uhr_age[0], mp_age[0])
    age_score = min(1.0, max(0.3, age_overlap / 20)) if age_overlap > 0 else 0.4
    
    # Timeline proximity (closer = better) - use full dates
    timeline_score = 0.5
    if mp_date and uhr_date:
        # Calculate approximate days difference
        days_diff = (uhr_date[0] - mp_date[0]) * 365 + (uhr_date[1] - mp_date[1]) * 30 + (uhr_date[2] - mp_date[2])
        
        if days_diff <= 90:  # Within 3 months
            timeline_score = 1.0
        elif days_diff <= 365:  # Within 1 year
            timeline_score = 0.9
        elif days_diff <= 730:  # Within 2 years
            timeline_score = 0.8
        elif days_diff <= 1825:  # Within 5 years
            timeline_score = 0.6
        else:
            timeline_score = 0.4
        
        reasons.append(f"Timeline: Found {days_diff} days after disappearance")
    
    # Feature text matching (tattoos, scars, dental)
    feature_score = 0.5  # Default neutral
    uhr_features = uhr.get('featureText', '') or ''
    mp_features = (mp.get('tattoos', '') or '') + ' ' + (mp.get('scarsMarks', '') or '')
    
    if uhr_features and mp_features:
        # Simple word overlap for feature matching
        uhr_words = set(uhr_features.lower().split()) - {'no', 'none', 'unknown', 'the', 'a', 'and', 'or'}
        mp_words = set(mp_features.lower().split()) - {'no', 'none', 'unknown', 'the', 'a', 'and', 'or'}
        
        if uhr_words and mp_words:
            overlap = uhr_words & mp_words
            if overlap:
                # Found matching keywords!
                feature_score = min(1.0, 0.6 + len(overlap) * 0.1)
                matching_words = list(overlap)[:3]
                reasons.append(f"Feature match: {', '.join(matching_words)}")
    
    # Tattoo keyword matching (high value)
    tattoo_bonus = 0
    if uhr.get('hasTattoo'):
        uhr_tattoo_text = uhr_features.lower()
        mp_tattoo_text = (mp.get('tattoos', '') or '').lower()
        
        # Look for specific tattoo keywords
        tattoo_keywords = ['eagle', 'cross', 'heart', 'skull', 'dragon', 'rose', 'star', 'name', 
                          'tribal', 'butterfly', 'angel', 'snake', 'lion', 'tiger', 'flower']
        
        for keyword in tattoo_keywords:
            if keyword in uhr_tattoo_text and keyword in mp_tattoo_text:
                tattoo_bonus = 0.15
                reasons.append(f"Tattoo: {keyword}")
                break
    
    # Clothing text matching
    clothing_score = 0.5
    uhr_clothing = uhr.get('clothingText', '') or ''
    mp_clothing = (mp.get('clothingDescription', '') or '') + ' ' + (mp.get('lastSeenWearing', '') or '')
    
    if uhr_clothing and mp_clothing:
        # Look for brand matches
        brands = ['nike', 'adidas', 'levis', 'wrangler', 'hanes', 'old navy', 'gap', 'champion']
        for brand in brands:
            if brand in uhr_clothing.lower() and brand in mp_clothing.lower():
                clothing_score = 0.8
                reasons.append(f"Clothing: {brand}")
                break
    
    # Weighted score: age 20%, timeline 25%, height 15%, features 25%, clothing 15%
    score = (age_score * 0.20 + 
             timeline_score * 0.25 + 
             height_score * 0.15 + 
             feature_score * 0.25 + 
             clothing_score * 0.15 +
             tattoo_bonus)
    
    return score, reasons


def match_all(uhr_cases, mp_cases, min_score=0.4, max_per_uhr=5):
    """Match with smart filtering."""
    mp_index = build_mp_index(mp_cases)
    
    all_matches = []
    skipped = 0
    compared = 0
    
    iterator = tqdm(uhr_cases, desc="Matching", total=len(uhr_cases)) if HAS_TQDM else enumerate(uhr_cases)
    
    for item in iterator:
        uhr = item if HAS_TQDM else item[1]
        i = 0 if HAS_TQDM else item[0]
        
        uhr_id = uhr.get('idFormatted') or uhr.get('namus2Number') or uhr.get('Case_Numbe')
        uhr_sex = normalize_sex(uhr.get('sex') or uhr.get('biologicalSex') or uhr.get('Sex'))
        uhr_state = get_state(uhr)
        uhr_date = get_date(uhr, ['dateFound'])
        
        # Get filtered candidates
        candidates = get_candidate_mps(mp_index, uhr_sex, uhr_state)
        compared += len(candidates)
        
        matches = []
        for mp in candidates:
            result = score_pair(uhr, mp, uhr_date)
            if result and result[0] >= min_score:
                score, reasons = result
                mp_id = mp.get('idFormatted') or mp.get('namus2Number') or mp.get('case_id')
                mp_name = f"{mp.get('firstName', '')} {mp.get('lastName', '')}".strip()
                matches.append({
                    'uhr_id': uhr_id,
                    'mp_id': mp_id,
                    'mp_name': mp_name or None,
                    'score': round(score, 3),
                    'reasons': reasons,
                    'priority': 'HIGH' if score >= 0.7 else 'MEDIUM' if score >= 0.5 else 'LOW'
                })
        
        matches.sort(key=lambda x: x['score'], reverse=True)
        all_matches.extend(matches[:max_per_uhr])
    
    # Stats
    total_possible = len(uhr_cases) * len(mp_cases)
    reduction = (1 - compared / total_possible) * 100 if total_possible > 0 else 0
    print(f"\nComparisons: {compared:,} (reduced {reduction:.1f}% from {total_possible:,})")
    
    all_matches.sort(key=lambda x: x['score'], reverse=True)
    return all_matches


def load_data():
    data = {'uhr': [], 'mp': []}
    
    # Prefer flattened file (fast, has height)
    namus_uhr = load_json(f"{DATA_DIR}/namus_unidentified_flat.json")
    if namus_uhr and len(namus_uhr) > 1000:
        print(f"Loaded {len(namus_uhr)} NamUs UHR (flattened with height)")
        data['uhr'].extend(namus_uhr)
    else:
        namus_uhr = load_json(f"{DATA_DIR}/namus_unidentified_summaries.json")
        if namus_uhr:
            print(f"Loaded {len(namus_uhr)} NamUs UHR (summaries)")
            data['uhr'].extend(namus_uhr)
    
    bc = load_json(f"{DATA_DIR}/bc_uhr_cases.json")
    if bc and isinstance(bc, dict):
        bc_uhr = [f['attributes'] for f in bc.get('features', [])]
        print(f"Loaded {len(bc_uhr)} BC UHR")
        data['uhr'].extend(bc_uhr)
    
    namus_mp = load_json(f"{DATA_DIR}/namus_missing_summaries.json")
    if namus_mp:
        print(f"Loaded {len(namus_mp)} NamUs Missing")
        data['mp'].extend(namus_mp)
    
    rcmp = load_json(f"{DATA_DIR}/rcmp_missing_persons.json")
    if rcmp:
        print(f"Loaded {len(rcmp)} RCMP Missing")
        data['mp'].extend(rcmp)
    
    charley = load_json(f"{DATA_DIR}/charley_washington.json")
    if charley:
        print(f"Loaded {len(charley)} Charley Project")
        data['mp'].extend(charley)
    
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-score", type=float, default=0.45)
    parser.add_argument("--max-per-uhr", type=int, default=5)
    parser.add_argument("--output", default=f"{OUTPUT_DIR}/leads.json")
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--require-height", action="store_true", help="Only match UHR with height data")
    parser.add_argument("--require-gender", action="store_true", help="Only match UHR with known sex")
    parser.add_argument("--require-features", action="store_true", help="Only match UHR with tattoos/scars/dental")
    parser.add_argument("--require-clothing", action="store_true", help="Only match UHR with clothing")
    args = parser.parse_args()
    
    print("=" * 60)
    print("UHR-MP Matcher (Smart Filtering)")
    print(f"Time: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 60)
    
    data = load_data()
    
    # Apply UHR filters
    original_count = len(data['uhr'])
    
    if args.require_height:
        data['uhr'] = [u for u in data['uhr'] if u.get('heightFrom')]
        print(f"Filter --require-height: {original_count} -> {len(data['uhr'])} UHR")
        original_count = len(data['uhr'])
    
    if args.require_gender:
        data['uhr'] = [u for u in data['uhr'] if u.get('sex') and u.get('sex').lower() not in ['unknown', 'unsure', 'u']]
        print(f"Filter --require-gender: {original_count} -> {len(data['uhr'])} UHR")
        original_count = len(data['uhr'])
    
    if args.require_features:
        data['uhr'] = [u for u in data['uhr'] if u.get('hasTattoo') or u.get('hasScar') or u.get('hasDental')]
        print(f"Filter --require-features: {original_count} -> {len(data['uhr'])} UHR")
        original_count = len(data['uhr'])
    
    if args.require_clothing:
        data['uhr'] = [u for u in data['uhr'] if u.get('hasClothing')]
        print(f"Filter --require-clothing: {original_count} -> {len(data['uhr'])} UHR")
    
    print(f"\nTotal: {len(data['uhr'])} UHR × {len(data['mp'])} MP = {len(data['uhr'])*len(data['mp']):,} potential pairs")
    
    if args.test:
        data['uhr'] = data['uhr'][:1000]
        print(f"Test: {len(data['uhr'])} UHR")
    
    matches = match_all(data['uhr'], data['mp'], args.min_score, args.max_per_uhr)
    
    by_pri = defaultdict(int)
    for m in matches:
        by_pri[m['priority']] += 1
    
    print(f"\n{len(matches)} matches: HIGH={by_pri['HIGH']}, MED={by_pri['MEDIUM']}, LOW={by_pri['LOW']}")
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(matches, f, indent=2)
    print(f"Saved to {args.output}")
    
    if matches[:5]:
        print("\nTop 5:")
        for m in matches[:5]:
            print(f"  {m['uhr_id']} <-> {m['mp_id']} ({m['mp_name']}) [{m['score']:.2f}]")


if __name__ == "__main__":
    main()
