
import json
import sys
import os
from datetime import datetime

# Import match logic
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from match_cases import score_pair, get_date

UHR_FILE = 'data/raw/namus_unidentified.json'
MP_FILE = 'data/raw/namus_missing.json'

def find_case(file_path, id_val):
    with open(file_path) as f:
        data = json.load(f)
        for c in data:
            if str(c.get('namus2Number')) == str(id_val) or \
               c.get('idFormatted') == id_val or \
               str(c.get('id')) == str(id_val):
                return c
    return None

def main():
    uhr_id = 'UP4335'
    mp_id = 'MP17595'
    
    print(f"Loading {uhr_id} and {mp_id}...")
    uhr = find_case(UHR_FILE, uhr_id.replace('UP',''))
    mp = find_case(MP_FILE, mp_id.replace('MP',''))
    
    if not uhr or not mp:
        print("Failed to load cases.")
        return

    print(f"\n--- Raw Data ---")
    print(f"UHR Date Found: {uhr.get('circumstances', {}).get('dateFound')}")
    print(f"MP Date Missing: {mp.get('sighting', {}).get('date')}")
    
    print(f"\n--- Parsed Dates ---")
    u_date = get_date(uhr, ['circumstances', 'dateFound'])
    m_date = get_date(mp, ['sighting', 'date'])
    print(f"Parsed UHR: {u_date}")
    print(f"Parsed MP: {m_date}")
    
    print(f"\n--- Scoring ---")
    result = score_pair(uhr, mp, u_date)
    print(f"Result: {result}")

if __name__ == "__main__":
    main()
