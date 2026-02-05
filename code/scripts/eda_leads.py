
import sqlite3
import json
import re
from collections import Counter
from datetime import datetime

DB_PATH = "data/filament.db"
REPORT_PATH = "data/reports/significant_leads.md"

def get_connection():
    return sqlite3.connect(DB_PATH)

def analyze_summary_stats(conn):
    print("=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)
    
    cursor = conn.cursor()
    
    # UHR Summary
    cursor.execute("SELECT count(*), min(discovery_date), max(discovery_date) FROM unidentified_cases")
    uhr_count, uhr_min_date, uhr_max_date = cursor.fetchone()
    print(f"Unidentified Human Remains (UHR): {uhr_count:,} cases")
    print(f"  Date Range: {uhr_min_date} to {uhr_max_date}")
    
    # MP Summary
    cursor.execute("SELECT count(*), min(last_seen_date), max(last_seen_date) FROM missing_persons")
    mp_count, mp_min_date, mp_max_date = cursor.fetchone()
    print(f"Missing Persons (MP): {mp_count:,} cases")
    print(f"  Date Range: {mp_min_date} to {mp_max_date}")
    print()

def analyze_temporal_trends(conn):
    print("=" * 80)
    print("TEMPORAL TRENDS (Top Years)")
    print("=" * 80)
    
    cursor = conn.cursor()
    
    # UHR Top Years
    cursor.execute("""
        SELECT substr(discovery_date, 1, 4) as year, count(*) 
        FROM unidentified_cases 
        WHERE discovery_date IS NOT NULL 
        GROUP BY year 
        ORDER BY count(*) DESC 
        LIMIT 10
    """)
    print("UHR - Top Years Found:")
    for year, count in cursor.fetchall():
        print(f"  {year}: {count}")
    
    # MP Top Years
    cursor.execute("""
        SELECT substr(last_seen_date, 1, 4) as year, count(*) 
        FROM missing_persons 
        WHERE last_seen_date IS NOT NULL 
        GROUP BY year 
        ORDER BY count(*) DESC 
        LIMIT 10
    """)
    print("\nMP - Top Years Last Seen:")
    for year, count in cursor.fetchall():
        print(f"  {year}: {count}")
    print()

def analyze_keyword_leads(conn, keywords):
    print("=" * 80)
    print(f"KEYWORD OVERLAP: {', '.join(keywords)}")
    print("=" * 80)
    
    cursor = conn.cursor()
    
    for kw in keywords:
        # Search UHR
        cursor.execute("SELECT count(*) FROM unidentified_cases WHERE description LIKE ?", (f'%{kw}%',))
        uhr_mentions = cursor.fetchone()[0]
        
        # Search MP
        cursor.execute("SELECT count(*) FROM missing_persons WHERE description LIKE ?", (f'%{kw}%',))
        mp_mentions = cursor.fetchone()[0]
        
        print(f"'{kw}':")
        print(f"  UHR Mentions: {uhr_mentions}")
        print(f"  MP Mentions:  {mp_mentions}")
        print(f"  Lead potential: High if both datasets have specific details.")
    print()

def analyze_candidate_overlaps(conn):
    """Simple filter for cases with distinct tags like tattoos and specific demographics."""
    print("=" * 80)
    print("POTENTIAL CANDIDATE PAIRS (Demographic + Keyword Filter)")
    print("=" * 80)
    
    cursor = conn.cursor()
    
    # Example: Females with tattoos in both datasets
    # This is demo-level filtering, real RAG would use embeddings
    
    uhr_query = """
        SELECT case_number, estimated_sex, estimated_age_min, estimated_age_max, description 
        FROM unidentified_cases 
        WHERE description LIKE '%tattoo%' AND estimated_sex = 'Female'
        LIMIT 5
    """
    
    mp_query = """
        SELECT file_number, name, sex, age_at_disappearance, description 
        FROM missing_persons 
        WHERE description LIKE '%tattoo%' AND sex = 'Female'
        LIMIT 5
    """
    
    cursor.execute(uhr_query)
    uhr_leads = cursor.fetchall()
    
    cursor.execute(mp_query)
    mp_leads = cursor.fetchall()
    
    print("Sample UHR Females with Tattoos:")
    for l in uhr_leads:
        print(f"  {l[0]}: {l[1]}, Age {l[2]}-{l[3]}, Desc: {l[4][:100]}...")
        
    print("\nSample MP Females with Tattoos:")
    for l in mp_leads:
        print(f"  {l[0]}: {l[1]}, Age {l[3]}, Desc: {l[4][:100]}...")
    print()

def generate_markdown_report(conn):
    print(f"Generating Markdown report at {REPORT_PATH}...")
    
    cursor = conn.cursor()
    
    with open(REPORT_PATH, 'w') as f:
        f.write("# Significant Leads Report\n\n")
        f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Summary Stats
        f.write("## Summary Statistics\n")
        cursor.execute("SELECT count(*) FROM unidentified_cases")
        uhr_count = cursor.fetchone()[0]
        cursor.execute("SELECT count(*) FROM missing_persons")
        mp_count = cursor.fetchone()[0]
        f.write(f"- **Unidentified Human Remains (UHR)**: {uhr_count:,} cases\n")
        f.write(f"- **Missing Persons (MP)**: {mp_count:,} cases\n\n")
        
        # Demographic Overlays (Sample)
        f.write("## Potential Candidate Pairs (Tattoo + Female)\n\n")
        f.write("### Sample UHR Females with Tattoos\n\n")
        f.write("| Case Number | Sex | Age Range | Description snippet |\n")
        f.write("|-------------|-----|-----------|---------------------|\n")
        
        uhr_query = """
            SELECT case_number, estimated_sex, estimated_age_min, estimated_age_max, description 
            FROM unidentified_cases 
            WHERE description LIKE '%tattoo%' AND estimated_sex = 'Female'
            LIMIT 10
        """
        cursor.execute(uhr_query)
        for row in cursor.fetchall():
            desc = row[4][:100].replace('\n', ' ') + "..."
            f.write(f"| {row[0]} | {row[1]} | {row[2]}-{row[3]} | {desc} |\n")
        
        f.write("\n### Sample MP Females with Tattoos\n\n")
        f.write("| File Number | Name | Age | Description snippet |\n")
        f.write("|-------------|------|-----|---------------------|\n")
        
        mp_query = """
            SELECT file_number, name, age_at_disappearance, description 
            FROM missing_persons 
            WHERE description LIKE '%tattoo%' AND sex = 'Female'
            LIMIT 10
        """
        cursor.execute(mp_query)
        for row in cursor.fetchall():
            desc = row[3][:100].replace('\n', ' ') + "..."
            f.write(f"| {row[0]} | {row[1]} | {row[2]} | {desc} |\n")
            
        f.write("\n## Keyword Analysis\n")
        f.write("| Keyword | UHR Mentions | MP Mentions |\n")
        f.write("|---------|--------------|-------------|\n")
        for kw in ['tattoo', 'scar', 'glasses', 'denture', 'prosthetic']:
            cursor.execute("SELECT count(*) FROM unidentified_cases WHERE description LIKE ?", (f'%{kw}%',))
            uhr_mentions = cursor.fetchone()[0]
            cursor.execute("SELECT count(*) FROM missing_persons WHERE description LIKE ?", (f'%{kw}%',))
            mp_mentions = cursor.fetchone()[0]
            f.write(f"| {kw} | {uhr_mentions} | {mp_mentions} |\n")

    print("Report generated successfully.")

def main():
    conn = get_connection()
    try:
        analyze_summary_stats(conn)
        analyze_temporal_trends(conn)
        analyze_keyword_leads(conn, ['tattoo', 'scar', 'glasses', 'denture', 'prosthetic'])
        analyze_candidate_overlaps(conn)
        generate_markdown_report(conn)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
