
import sqlite3
import json
import os
import sys
from datetime import datetime

# Ensure the code directory is in the path for the filament package
scripts_dir = os.path.dirname(os.path.abspath(__file__))
code_dir = os.path.dirname(scripts_dir)
if code_dir not in sys.path:
    sys.path.insert(0, code_dir)

from core.search import NarrativeGenerator

DB_PATH = "data/filament.db"
LEADS_PATH = "data/processed/leads_advanced.json"
REPORTS_DIR = "data/reports/lead_narratives"

def get_full_case_details(conn, case_number, table):
    cursor = conn.cursor()
    col = "case_number" if table == "unidentified_cases" else "file_number"
    cursor.execute(f"SELECT * FROM {table} WHERE {col} = ?", (case_number,))
    row = cursor.fetchone()
    if not row:
        return {}
    
    # Get column names
    cursor.execute(f"PRAGMA table_info({table})")
    cols = [c[1] for c in cursor.fetchall()]
    return dict(zip(cols, row))

def generate_reports():
    if not os.path.exists(LEADS_PATH):
        print(f"Error: Leads file not found at {LEADS_PATH}")
        return

    with open(LEADS_PATH, 'r') as f:
        leads = json.load(f)

    # Use localhost as Ollama runs in the same container
    generator = NarrativeGenerator(ollama_host="http://localhost:11434") 
    # Note: If running from host, use localhost. If running from another container, use ollama.
    # Since I'm executing this via podman-compose/exec, it depends on context.
    # I'll try to detect or just use a robust default.
    
    os.makedirs(REPORTS_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    
    try:
        # Generate reports for top 5 leads
        for i, lead in enumerate(leads[:5], 1):
            uhr_num = lead['uhr_case']
            mp_file = lead['mp_file']
            
            print(f"Generating narrative for Lead {i}: {uhr_num} <-> {mp_file}...")
            
            uhr_data = get_full_case_details(conn, uhr_num, "unidentified_cases")
            mp_data = get_full_case_details(conn, mp_file, "missing_persons")
            
            narrative = generator.generate_story_line(uhr_data, mp_data, lead['shared_features'])
            
            report_content = f"""# Investigative Lead Report: {uhr_num} / {mp_file}

**Report Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Match Score**: {lead['score']}

## Investigative Narrative
{narrative}

---

## Unidentified Human Remains ({uhr_num})
- **Sex**: {uhr_data.get('estimated_sex')}
- **Age**: {uhr_data.get('estimated_age_min')} - {uhr_data.get('estimated_age_max')}
- **Discovery Date**: {uhr_data.get('discovery_date')}
- **Description**: 
{uhr_data.get('description')}

## Missing Person ({mp_file})
- **Name**: {mp_data.get('name')}
- **Sex**: {mp_data.get('sex')}
- **Age**: {mp_data.get('age_at_disappearance')}
- **Last Seen**: {mp_data.get('last_seen_date')}
- **Description**:
{mp_data.get('description')}
"""
            filename = f"lead_{uhr_num}_{mp_file}.md"
            with open(os.path.join(REPORTS_DIR, filename), 'w') as f:
                f.write(report_content)
                
        print(f"Narrative reports generated in {REPORTS_DIR}")
        
    finally:
        conn.close()

if __name__ == "__main__":
    generate_reports()
