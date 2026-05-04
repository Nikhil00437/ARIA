# scraper.py
import os
import sys
from ddgs import DDGS
import trafilatura

def search_and_save(query: str, out_dir: str = "scraped_data", limit: int = 5):
    if not query.strip():
        print("Error: Empty query. Pass valid term.")
        sys.exit(1)
        
    os.makedirs(out_dir, exist_ok=True)
    hits = []
    try:
        with DDGS() as engine:
            hits = list(engine.text(query, max_results=limit))
    except Exception as err:
        print(f"Search fail: {err}")
        sys.exit(1)
        
    if not hits:
        print("Zero results. Check query/network/retry.")
        sys.exit(1)

    for hit in hits:
        url = hit.get("href")
        title = hit.get("title", "untitled").replace("/", "_").replace("\\", "_").replace(":", "_").replace("?", "_").replace("*", "_").replace('"', "_").replace("<", "_").replace(">", "_").replace("|", "_").replace(" ", "_")[:100]
        try:
            raw = trafilatura.fetch_url(url)
            md = trafilatura.extract(raw, output_format="markdown") or "[No text extracted]"
        except Exception as err:
            md = f"[Fetch fail: {err}]"
        
        path = os.path.join(out_dir, f"{title}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# {title}\n\nURL: {url}\n\n{md}\n")
            
    print(f"Saved {len(hits)} files to {out_dir}")

if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else ""
    search_and_save(q)