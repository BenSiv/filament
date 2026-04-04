"""
configure_fossil_tools.py

Installs the Filament domain-specific TH1 tool extensions into the
Fossil AI knowledge base (data/knowledge.fossil) by writing the
contents of cfg/filament-tools.th1 into the `th1-setup` config key.

After running this script, the Fossil AI Agent chat UI will expose 6
new tools specific to the Filament cold-case investigation pipeline:

  - filament_stats          Summary statistics of the knowledge base
  - filament_search_cases   Keyword search across UHR/MP/reddit/lead notes
  - filament_case_detail    Full narrative for a specific case number
  - filament_list_leads     Top AI-generated forensic lead candidates
  - filament_lead_detail    Full analysis + linked cases for one lead
  - filament_recent_notes   Most recently ingested notes

Usage:
  python3 code/scripts/configure_fossil_tools.py

Requirements:
  - data/knowledge.fossil must exist (run fossil init + ingest first)
  - cfg/filament-tools.th1 must exist (shipped with the repo)
"""

import os
import sys
import sqlite3

scripts_dir = os.path.dirname(os.path.abspath(__file__))
code_dir    = os.path.dirname(scripts_dir)
root_dir    = os.path.dirname(code_dir)

FOSSIL_DB   = os.path.join(root_dir, "data", "knowledge.fossil")
TH1_SETUP   = os.path.join(root_dir, "cfg", "filament-tools.th1")


def main():
    # Validate paths
    if not os.path.exists(FOSSIL_DB):
        print(f"ERROR: Fossil knowledge base not found at {FOSSIL_DB}")
        print("  Create it with:  fossil init data/knowledge.fossil")
        print("  Then ingest:     python3 code/scripts/ingest_all_to_fossil.py")
        sys.exit(1)

    if not os.path.exists(TH1_SETUP):
        print(f"ERROR: TH1 setup file not found at {TH1_SETUP}")
        sys.exit(1)

    with open(TH1_SETUP, "r", encoding="utf-8") as f:
        th1_script = f.read()

    print(f"Reading TH1 tools from: {TH1_SETUP}")
    print(f"  {th1_script.count('agent_capability_register')} tool(s) found")

    print(f"\nConnecting to: {FOSSIL_DB}")
    conn = sqlite3.connect(FOSSIL_DB)
    cur = conn.cursor()

    # Upsert the th1-setup config key
    cur.execute(
        "INSERT OR REPLACE INTO config(name, value, mtime) VALUES(?, ?, strftime('%s','now'))",
        ("th1-setup", th1_script),
    )

    # Ensure AI and agent settings are sane defaults if not already set
    defaults = [
        ("ai-enable",              "1"),
        ("agent-provider",         "ollama"),
        ("agent-model",            "qwen3.5:0.8b"),
        ("agent-embedding-model",  "nomic-embed-text"),
    ]
    for key, val in defaults:
        cur.execute(
            "INSERT OR IGNORE INTO config(name, value, mtime) VALUES(?, ?, strftime('%s','now'))",
            (key, val),
        )

    conn.commit()
    conn.close()

    print("\n✓ TH1 tools installed into knowledge.fossil")
    print("\nAvailable tools (visible in `fossil agent capabilities -R data/knowledge.fossil`):")
    tools = [
        ("filament_stats",        "Knowledge base summary statistics"),
        ("filament_search_cases", "Keyword search across UHR/MP/reddit/lead notes"),
        ("filament_case_detail",  "Full narrative for a specific case by source_ref"),
        ("filament_list_leads",   "Top AI-generated forensic lead candidates"),
        ("filament_lead_detail",  "Full analysis + linked cases for one lead"),
        ("filament_recent_notes", "Most recently ingested notes"),
    ]
    for name, desc in tools:
        print(f"  {name:<28} {desc}")

    print(f"\nNext steps:")
    print(f"  1. Start the Fossil web UI:")
    print(f"       fossil ui -R data/knowledge.fossil")
    print(f"  2. Open the AI agent chat and ask about cases.")
    print(f"  3. Use tool calls like:")
    print(f'       {{"tool":"filament_stats"}}')
    print(f'       {{"tool":"filament_search_cases","arguments":{{"query":"Jane Doe","source_type":"missing_person"}}}}')
    print(f'       {{"tool":"filament_list_leads","arguments":{{"limit":15}}}}')


if __name__ == "__main__":
    main()
