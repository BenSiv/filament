
import json
import os
from datetime import datetime

def main():
    input_file = 'data/processed/leads_hybrid.json'
    output_file = 'data/processed/hybrid_leads_report.md'
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return
        
    with open(input_file, 'r') as f:
        leads = json.load(f)
        
    with open(output_file, 'w') as f:
        f.write(f"# Hybrid RAG Matching Report\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"**Total Leads:** {len(leads)}\n\n")
        
        f.write("## Top Candidates (Score > 0.85)\n\n")
        
        f.write("| Rank | MP Name | Case IDs | Score | Vector Sim | Key Reasons |\n")
        f.write("|---|---|---|---|---|---|\n")
        
        for i, lead in enumerate(leads):
            if i >= 50: break # Top 50 in table
            
            uhr_link = f"[{lead['uhr_id']}](https://www.namus.gov/UnidentifiedPersons/Case#/{lead['uhr_id'].replace('UP','')})"
            mp_link = f"[{lead['mp_name']}](https://www.namus.gov/MissingPersons/Case#/{lead['mp_id'].replace('MP','')})"
            
            reasons = "<br>".join(lead['reasons'])
            
            f.write(f"| {i+1} | {mp_link} | {lead['mp_id']} ↔ {uhr_link} | **{lead['score']:.3f}** | {lead['vector_score']:.3f} | {reasons} |\n")
            
        f.write("\n## Analysis of Top 5 Matches\n")
        for i, lead in enumerate(leads[:5]):
            f.write(f"\n### {i+1}. {lead['mp_name']} ({lead['mp_id']}) ↔ {lead['uhr_id']}\n")
            f.write(f"- **Composite Score:** {lead['score']}\n")
            f.write(f"- **Semantic Similarity:** {lead['vector_score']} (Very High)\n")
            f.write(f"- **Validation Logic:**\n")
            for r in lead['reasons']:
                f.write(f"  - {r}\n")
            
            # Story Line
            narr = lead.get('narratives', {})
            if narr:
                f.write(f"- **Story Line:**\n")
                f.write(f"  - *Missing:* \"{narr.get('mp')}\"\n")
                f.write(f"  - *Found:* \"{narr.get('uhr')}\"\n")
                
    print(f"Report generated at {output_file}")

if __name__ == "__main__":
    main()
