import urllib.request
import json
import sqlite3
import os
from sparkhub_paths import get_path

DB_PATH = str(get_path("mempalace.db"))
SUBREDDITS = ["godot", "blender"]
LIMIT = 5

def fetch_reddit_json(subreddit):
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={LIMIT}"
    req = urllib.request.Request(
        url, 
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) SparkHub/3.0'}
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data.get("data", {}).get("children", [])
    except Exception as e:
        print(f"[MURPHY] Erro ao buscar /r/{subreddit}: {e}")
        return []

def collect_forums():
    if not os.path.exists(DB_PATH):
        print("Erro: mempalace.db não encontrado.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Criar a tabela se não existir (garantia)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wing TEXT,
            room TEXT,
            content TEXT,
            timestamp TEXT
        )
    """)
    
    new_inserts = 0
    
    for sub in SUBREDDITS:
        posts = fetch_reddit_json(sub)
        print(f"Buscando posts de /r/{sub}... Encontrados: {len(posts)}")
        for post in posts:
            post_data = post.get("data", {})
            title = post_data.get("title", "")
            url = post_data.get("url", "")
            post_id = post_data.get("id", "")
            
            if not title: continue
            
            content_str = f"[{post_id}] {title} | Link: {url}"
            
            # Deduplicação simples por URL
            cur.execute("SELECT id FROM memories WHERE room = 'reddit_snippets' AND content LIKE ?", (f"%{url}%",))
            if cur.fetchone():
                continue
                
            timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            cur.execute(
                "INSERT INTO memories (wing, room, content, timestamp) VALUES (?, ?, ?, ?)",
                ("Social", "reddit_snippets", content_str, timestamp)
            )
            new_inserts += 1

    conn.commit()
    conn.close()
    print(f"Sucesso! {new_inserts} novos snippets de fóruns ingeridos no MemPalace.")

if __name__ == "__main__":
    collect_forums()
