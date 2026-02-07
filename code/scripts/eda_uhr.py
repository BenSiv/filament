#!/usr/bin/env python3
"""
Exploratory Data Analysis - BC Unidentified Human Remains

Analyzes the real data fetched from BC Coroners Service ArcGIS.
"""

import json
from datetime import datetime
from collections import Counter

# Load the data
with open('data/raw/bc_uhr_cases.json', 'r') as f:
    data = json.load(f)

features = data['features']
cases = [f['attributes'] for f in features]

print("=" * 70)
print("BC UNIDENTIFIED HUMAN REMAINS - EXPLORATORY DATA ANALYSIS")
print("=" * 70)
print(f"Total Cases: {len(cases)}")
print()

# =============================================================================
# 1. SEX DISTRIBUTION
# =============================================================================
print("1. SEX DISTRIBUTION")
print("-" * 40)
sex_counts = Counter(c['Sex'] for c in cases if c['Sex'])
for sex, count in sex_counts.most_common():
    pct = count / len(cases) * 100
    print(f"   {sex}: {count} ({pct:.1f}%)")
print()

# =============================================================================
# 2. AGE DISTRIBUTION
# =============================================================================
print("2. AGE RANGE DISTRIBUTION")
print("-" * 40)

# Calculate age midpoints
ages = []
for c in cases:
    min_age = c.get('Minimum_Ag')
    max_age = c.get('Maximum_Ag')
    if min_age and max_age:
        ages.append((min_age + max_age) / 2)

if ages:
    avg_age = sum(ages) / len(ages)
    min_avg = min(ages)
    max_avg = max(ages)
    
    # Age brackets
    brackets = {'0-20': 0, '21-40': 0, '41-60': 0, '61-80': 0, '80+': 0, 'Unknown': 0}
    for age in ages:
        if age <= 20: brackets['0-20'] += 1
        elif age <= 40: brackets['21-40'] += 1
        elif age <= 60: brackets['41-60'] += 1
        elif age <= 80: brackets['61-80'] += 1
        else: brackets['80+'] += 1
    
    unknown_age = len(cases) - len(ages)
    brackets['Unknown'] = unknown_age
    
    print(f"   Age data available for {len(ages)} cases")
    print(f"   Average estimated age: {avg_age:.1f} years")
    print(f"   Range: {min_avg:.0f} - {max_avg:.0f} years")
    print()
    print("   Age Distribution:")
    for bracket, count in brackets.items():
        pct = count / len(cases) * 100
        bar = '█' * int(pct / 2)
        print(f"   {bracket:>10}: {count:>3} ({pct:>5.1f}%) {bar}")
print()

# =============================================================================
# 3. RACE/ETHNICITY
# =============================================================================
print("3. RACE/ETHNICITY DISTRIBUTION")
print("-" * 40)
race_counts = Counter(c['Race'] for c in cases if c.get('Race') and c['Race'].strip())
for race, count in race_counts.most_common():
    pct = count / len(cases) * 100
    print(f"   {race}: {count} ({pct:.1f}%)")
print()

# =============================================================================
# 4. TEMPORAL ANALYSIS
# =============================================================================
print("4. TEMPORAL ANALYSIS (Discovery Year)")
print("-" * 40)

# Convert epoch milliseconds to year
years = []
for c in cases:
    date_found = c.get('Date_Found')
    if date_found:
        try:
            dt = datetime.fromtimestamp(date_found / 1000)
            years.append(dt.year)
        except:
            pass

if years:
    year_counts = Counter(years)
    decades = Counter((y // 10) * 10 for y in years)
    
    print(f"   Cases with date data: {len(years)}")
    print(f"   Earliest case: {min(years)}")
    print(f"   Most recent case: {max(years)}")
    print()
    print("   By Decade:")
    for decade in sorted(decades.keys()):
        count = decades[decade]
        pct = count / len(years) * 100
        bar = '█' * int(pct / 2)
        print(f"   {decade}s: {count:>3} ({pct:>5.1f}%) {bar}")
print()

# =============================================================================
# 5. GEOGRAPHIC DISTRIBUTION
# =============================================================================
print("5. GEOGRAPHIC DISTRIBUTION")
print("-" * 40)

# Approximate BC regions by lat/lon
lats = [c['Latitude'] for c in cases if c.get('Latitude')]
lons = [c['Longitude'] for c in cases if c.get('Longitude')]

if lats and lons:
    print(f"   Cases with coordinates: {len(lats)}")
    print(f"   Latitude range: {min(lats):.2f}°N to {max(lats):.2f}°N")
    print(f"   Longitude range: {min(lons):.2f}°W to {max(lons):.2f}°W")
    
    # Rough regional breakdown
    regions = {'Lower Mainland (49-49.5°N)': 0, 
               'Vancouver Island (48-50°N, <-123°W)': 0,
               'Interior (49-52°N)': 0, 
               'Northern BC (>52°N)': 0}
    
    for lat, lon in zip(lats, lons):
        if lat < 49.5 and lon > -123:
            regions['Lower Mainland (49-49.5°N)'] += 1
        elif lon < -123 and lat < 50:
            regions['Vancouver Island (48-50°N, <-123°W)'] += 1
        elif lat >= 52:
            regions['Northern BC (>52°N)'] += 1
        else:
            regions['Interior (49-52°N)'] += 1
    
    print()
    print("   Approximate Regional Distribution:")
    for region, count in sorted(regions.items(), key=lambda x: -x[1]):
        pct = count / len(lats) * 100
        print(f"   {region}: {count} ({pct:.1f}%)")
print()

# =============================================================================
# 6. PHYSICAL DESCRIPTORS
# =============================================================================
print("6. PHYSICAL DESCRIPTORS AVAILABILITY")
print("-" * 40)

descriptors = {
    'Eye Colour': sum(1 for c in cases if c.get('Eye_Colour', '').strip()),
    'Hair Colour': sum(1 for c in cases if c.get('Hair_Colou', '').strip()),
    'Height': sum(1 for c in cases if c.get('Minimum_He', '').strip()),
    'Clothing': sum(1 for c in cases if c.get('Clothing', '').strip()),
    'Tattoos': sum(1 for c in cases if c.get('Tattoos', '').strip()),
    'Scars': sum(1 for c in cases if c.get('Scars', '').strip()),
    'Other Comments': sum(1 for c in cases if c.get('Other_Comm', '').strip()),
}

for desc, count in sorted(descriptors.items(), key=lambda x: -x[1]):
    pct = count / len(cases) * 100
    bar = '█' * int(pct / 2)
    print(f"   {desc:>15}: {count:>3} ({pct:>5.1f}%) {bar}")
print()

# =============================================================================
# 7. HAIR/EYE COLOR BREAKDOWN
# =============================================================================
print("7. HAIR COLOR DISTRIBUTION (where available)")
print("-" * 40)
hair_counts = Counter(c['Hair_Colou'] for c in cases if c.get('Hair_Colou', '').strip())
for hair, count in hair_counts.most_common(10):
    print(f"   {hair}: {count}")
print()

# =============================================================================
# 8. CLOTHING ANALYSIS (Text Mining)
# =============================================================================
print("8. CLOTHING KEYWORDS (mentions)")
print("-" * 40)

clothing_texts = [c['Clothing'] for c in cases if c.get('Clothing', '').strip()]
all_clothing = ' '.join(clothing_texts).lower()

keywords = ['jeans', 'shirt', 'jacket', 'shoes', 'boots', 'pants', 'sweater', 
            'coat', 'socks', 'belt', 'watch', 'ring', 'naked', 'underwear']

for kw in sorted(keywords, key=lambda k: all_clothing.count(k), reverse=True):
    count = all_clothing.count(kw)
    if count > 0:
        print(f"   {kw}: {count} mentions")
print()

# =============================================================================
# 9. NOTABLE CASES
# =============================================================================
print("9. NOTABLE CASES (with unique identifiers)")
print("-" * 40)

# Cases with tattoos
tattoo_cases = [c for c in cases if c.get('Tattoos', '').strip()]
print(f"   Cases with tattoos: {len(tattoo_cases)}")
for c in tattoo_cases[:3]:
    print(f"     - {c['Case_Numbe']}: {c['Tattoos'][:60]}")

# Cases with scars
scar_cases = [c for c in cases if c.get('Scars', '').strip()]
print(f"\n   Cases with scars: {len(scar_cases)}")

# Cases with detailed clothing
detailed_clothing = [c for c in cases if len(c.get('Clothing', '')) > 100]
print(f"\n   Cases with detailed clothing descriptions: {len(detailed_clothing)}")

print()
print("=" * 70)
print("END OF EXPLORATORY DATA ANALYSIS")
print("=" * 70)
