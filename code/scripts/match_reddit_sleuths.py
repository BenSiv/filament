import os
import sys
import sqlite3
import json
import numpy as np
import requests
from sentence_transformers import SentenceTransformer

scripts_dir = os.path.dirname(os.path.abspath(__file__))
code_dir = os.path.dirname(scripts_dir)
if code_dir not in sys.path:
    sys.path.insert(0, code_dir)

def cosine_similarity(v1, v2):
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

def generate_reddit_leads(limit=50):
    db_path = "data/filament.db"
    reddit_path = "data/raw/reddit/missing_and_uhr_narratives.json"
    
    if not os.path.exists(db_path) or not os.path.exists(reddit_path):
        print("Required data not found. Ensure DB is built and Reddit scraper ran.")
        return
        
    print("Loading embedding model (all-MiniLM-L6-v2)...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    
    # 1. Load and Embed Reddit Narratives In-Memory (Bypass sqlite-vss)
    with open(reddit_path, "r") as f:
        reddit_posts = json.load(f)
    
    print(f"Embedding {len(reddit_posts)} Reddit narratives...")
    reddit_texts = [f"{p.get('title', '')}\n{p.get('selftext', '')}" for p in reddit_posts]
    reddit_embeddings = model.encode(reddit_texts)
    
    # 2. Get UHR Cases
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT case_number, description 
        FROM unidentified_cases 
        WHERE description IS NOT NULL AND length(description) > 50
        ORDER BY RANDOM() LIMIT ?
    """, (limit,))
    uhr_cases = cur.fetchall()
    conn.close()
    
    print(f"Executing RAG lead generation for {len(uhr_cases)} UHR cases...")
    leads = []
    
    for i, (case_num, desc) in enumerate(uhr_cases):
        # Embed UHR description
        q_emb = model.encode(desc)
        
        # Calculate similarities
        similarities = [cosine_similarity(q_emb, r_emb) for r_emb in reddit_embeddings]
        
        # Get top 3 indices
        top_indices = np.argsort(similarities)[-3:][::-1]
        
        for idx in top_indices:
            score = similarities[idx]
            if score < 0.35:
                continue
                
            post = reddit_posts[idx]
            title = post.get("title", "")
            print(f"\n[{case_num}] Found sleuth connection in: '{title[:50]}...' (Score: {score:.2f})")
            
            # Ask Ollama to evaluate the lead
            prompt = f"""
            You are a cold case forensic analyst. An internet sleuth posted a narrative that semantically aligns with an Unidentified Human Remains (UHR) case.
            
            UHR Case {case_num} Details:
            {desc[:800]}
            
            Reddit Sleuth Post: "{title}"
            {post.get("selftext", "")[:1500]}
            
            MISSION:
            Does this Reddit post suggest a viable identity (Missing Person name) or a critical circumstantial connection to this UHR?
            If YES: Provide a brief 2-sentence explanation of the connection.
            If NO: Reply exclusively with the exact string "NO_VIABLE_LEAD".
            """
            
            try:
                response = requests.post(f"http://localhost:11434/api/generate", json={
                    "model": "qwen3.5:0.8b",
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": 300}
                }, timeout=120).json()
                
                analysis = response.get("response", "")
                if not analysis:
                    analysis = response.get("thinking", "NO_VIABLE_LEAD")
                
                if "NO_VIABLE_LEAD" not in analysis:
                    leads.append({
                        "uhr_case": case_num,
                        "reddit_url": post.get("url"),
                        "reddit_title": title,
                        "vector_similarity": float(score),
                        "llm_analysis": analysis.strip()
                    })
                    print(f"  -> SUCCESS: LLM extracted a narrative lead or identity!")
                else:
                    print(f"  -> Rejected by LLM (No concrete identity/link found).")
            except Exception as e:
                print(f"Error calling LLM: {e}")
                
    out_dir = "data/reports"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "reddit_sleuth_leads.json")
    
    with open(out_path, "w") as f:
        json.dump(leads, f, indent=2)
        
    print(f"\nGenerated {len(leads)} viable Reddit-based leads. Saved to {out_path}.")
    
    # Generate MD Report
    if leads:
        report_path = os.path.join(out_dir, "reddit_leads_report.md")
        with open(report_path, "w") as f:
            f.write("# Unstructured Narrative (Reddit) Matches\n\n")
            for lead in leads:
                f.write(f"## UHR Case: {lead['uhr_case']}\n")
                f.write(f"- **Thread**: [{lead['reddit_title']}]({lead['reddit_url']})\n")
                f.write(f"- **Semantic Score**: {lead['vector_similarity']:.2f}\n")
                f.write(f"- **AI Analysis**:\n{lead['llm_analysis']}\n\n")
        print(f"Markdown report ready at {report_path}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10, help="Number of cases to evaluate")
    args = parser.parse_args()
    generate_reddit_leads(args.limit)
