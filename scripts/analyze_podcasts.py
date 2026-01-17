"""
Analyze ingested podcast transcripts.
"""
import json
import os
import sys
from pathlib import Path
from collections import Counter
import re

DATA_DIR = Path("data/raw/podcasts_podscribe")

def analyze_transcripts():
    if not DATA_DIR.exists():
        print(f"Data directory {DATA_DIR} does not exist.")
        return

    files = list(DATA_DIR.glob("*.json"))
    print(f"Found {len(files)} transcript files.")
    
    all_text = ""
    for file_path in files:
        with open(file_path, "r") as f:
            data = json.load(f)
            print(f"\n--- Analysis: {data.get('title', 'Unknown')} ---")
            text = data.get('text', '')
            print(f"Length: {len(text)} characters")
            
            # Simple keyword check
            keywords = ["missing", "vanished", "police", "last seen", "murder", "unidentified"]
            print("Keywords found:")
            for kw in keywords:
                count = text.lower().count(kw)
                if count > 0:
                    print(f"  - {kw}: {count}")
            
            all_text += text + " "

    # Aggregate stats
    print("\n=== Aggregate Analysis ===")
    words = re.findall(r'\w+', all_text.lower())
    common = Counter(words).most_common(10)
    print("Most common words:", common)

if __name__ == "__main__":
    analyze_transcripts()
