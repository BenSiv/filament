import json
import sqlite3
import os
import sys

scripts_dir = os.path.dirname(os.path.abspath(__file__))
code_dir = os.path.dirname(scripts_dir)
if code_dir not in sys.path:
    sys.path.insert(0, code_dir)

from core.search.semantic_search import SemanticSearch

def ingest_reddit():
    file_path = "data/raw/reddit/missing_and_uhr_narratives.json"
    if not os.path.exists(file_path):
        print(f"Data not found at {file_path}. Run the scraper first.")
        return
        
    with open(file_path, "r") as f:
        posts = json.load(f)
        
    print(f"Ingesting {len(posts)} Reddit posts into SQLite Vector Store...")
    
    # Initialize DB schema if not exists
    import subprocess
    if not os.path.exists("data/filament.db"):
        print("Database not found, building sqlite DB first...")
        subprocess.run(["python3", os.path.join(scripts_dir, "build_sqlite_db.py")])
        
    search = SemanticSearch("data/filament.db")
    search.store.create_table("reddit_narratives", 384) # 384 dimensions for all-MiniLM-L6-v2
    
    for i, post in enumerate(posts):
        metadata = {
            "title": post.get("title"),
            "url": post.get("url"),
            "score": post.get("score"),
            "source": post.get("source")
        }
        text = f"{post.get('title', '')}\n{post.get('selftext', '')}"
        
        # doc_id must be a string for semantic_search index_document mapping
        search.index_document("reddit_narratives", str(post.get("id")), text, metadata)
        
        if (i + 1) % 10 == 0:
            print(f"  -> Indexed {i+1}/{len(posts)} posts.")
            
    # Close connection
    search.close()
    print("Reddit narrative ingestion complete. The data is now ready for semantic vector search.")

if __name__ == "__main__":
    ingest_reddit()
