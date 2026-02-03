
import json
import os
from datetime import datetime

def main():
    input_file = 'data/processed/leads_ml.json'
    output_file = 'data/processed/ml_leads_report.md'
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return
        
    with open(input_file, 'r') as f:
        leads = json.load(f)
        
    with open(output_file, 'w') as f:
        f.write(f"# Machine Learning Matching Report\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"**Total Leads:** {len(leads)}\n\n")
        
        f.write("> [!NOTE]\n")
        f.write("> Scores represent probability (0.0 - 1.0) from RandomForest Model trained on synthetic data.\n")
        f.write("> Key Factors: Keyword Overlap & Timeline Plausibility.\n\n")
        
        f.write("## Top Candidates (Prob > 0.5)\n")
        
        f.write("| Rank | MP Name | Case IDs | Score | Key Factors |\n")
        f.write("|---|---|---|---|---|\n")
        
        for i, lead in enumerate(leads):
            if i >= 50: break
            
            uhr_link = f"[{lead['uhr_id']}](https://www.namus.gov/UnidentifiedPersons/Case#/{lead['uhr_id'].replace('UP','')})"
            mp_link = f"[{lead['mp_name']}](https://www.namus.gov/MissingPersons/Case#/{lead['mp_id'].replace('MP','')})"
            
            feats = lead['features']
            factors = []
            if feats['keyword_overlap'] > 0:
                factors.append(f"**Keywords: {int(feats['keyword_overlap'])}**")
            if feats['days_diff'] < 365:
                factors.append(f"Time Gap: {int(feats['days_diff'])}d")
            elif feats['days_diff'] < 1095: # 3 years
                 factors.append(f"Time Gap: {int(feats['days_diff']/365)}y")
                 
            if feats['vector_sim'] > 0.7:
                 factors.append(f"Sim: {feats['vector_sim']:.2f}")
            
            factor_str = ", ".join(factors)
            
            f.write(f"| {i+1} | {mp_link} | {lead['mp_id']} ↔ {uhr_link} | **{lead['score']:.4f}** | {factor_str} |\n")
            
    print(f"Report generated at {output_file}")

if __name__ == "__main__":
    main()
