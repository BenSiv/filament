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
    for field in ['stateDisplayNameOfRecovery', 'stateOfRecovery', 
                  'stateDisplayNameOfLastContact', 'stateOfLastContact', 'state']:
        val = case.get(field)
        if val:
            val = str(val).strip().upper()
            if len(val) == 2:
                return val
            # Map full names to codes (simplified)
            state_map = {
                'CALIFORNIA': 'CA', 'TEXAS': 'TX', 'FLORIDA': 'FL', 'NEW YORK': 'NY',
                'WASHINGTON': 'WA', 'OREGON': 'OR', 'ARIZONA': 'AZ', 'NEVADA': 'NV',
                'BRITISH COLUMBIA': 'BC', 'ONTARIO': 'ON', 'ALBERTA': 'AB'
            }
            if val in state_map:
                return state_map[val]
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


def score_pair(uhr, mp, uhr_year):
    """Score a candidate pair. Returns (score, reasons) or None."""
    reasons = []
    
    # Date filter: MP must be missing before UHR found
    mp_year = get_year(mp, ['dateOfLastContact', 'dateMissing'])
    if mp_year and uhr_year and mp_year > uhr_year:
        return None
    
    # Age filter
    uhr_age = get_age_range(uhr, True)
    mp_age = get_age_range(mp, False)
    
    # Check overlap with tolerance
    if uhr_age[1] < mp_age[0] - 10 or uhr_age[0] > mp_age[1] + 15:
        return None
    
    # Calculate score components
    age_overlap = min(uhr_age[1], mp_age[1]) - max(uhr_age[0], mp_age[0])
    age_score = min(1.0, max(0.3, age_overlap / 20)) if age_overlap > 0 else 0.4
    
    # Year proximity (closer = better)
    year_score = 0.5
    if mp_year and uhr_year:
        years_diff = uhr_year - mp_year
        if years_diff <= 2:
            year_score = 1.0
        elif years_diff <= 5:
            year_score = 0.8
        elif years_diff <= 10:
            year_score = 0.6
        reasons.append(f"{years_diff}yr gap")
    
    score = age_score * 0.4 + year_score * 0.4 + 0.5 * 0.2
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
        uhr_year = get_year(uhr, ['dateFound'])
        
        # Get filtered candidates
        candidates = get_candidate_mps(mp_index, uhr_sex, uhr_state)
        compared += len(candidates)
        
        matches = []
        for mp in candidates:
            result = score_pair(uhr, mp, uhr_year)
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
    
    namus_uhr = load_json(f"{DATA_DIR}/namus_unidentified_summaries.json")
    if namus_uhr:
        print(f"Loaded {len(namus_uhr)} NamUs UHR")
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
    args = parser.parse_args()
    
    print("=" * 60)
    print("UHR-MP Matcher (Smart Filtering)")
    print(f"Time: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 60)
    
    data = load_data()
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
