import os
import time
import json
import sqlite3
import urllib.request
import urllib.error
from dotenv import load_dotenv
import sparkhub_db

load_dotenv()

NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY")
EMBEDDING_MODEL = "nvidia/llama-nemotron-embed-vl-1b-v2"
BATCH_SIZE = 5
DELAY_BETWEEN_BATCHES = 2.0  # seconds

def get_embedding(text: str) -> list[float]:
    if not NVIDIA_API_KEY or NVIDIA_API_KEY == "nvapi-sua-chave-gerada-aqui":
        raise ValueError("NVIDIA_API_KEY invalida")
        
    url = "https://integrate.api.nvidia.com/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json"
    }
    # Clip texto para não estourar o contexto máximo do modelo gratuito
    payload = {
        "model": EMBEDDING_MODEL,
        "input": text[:8000]
    }
    
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result["data"][0]["embedding"]
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode()
        print(f"[EMBED WORKER] Erro HTTP {e.code}: {error_msg}")
        return []
    except Exception as e:
        print(f"[EMBED WORKER] Erro na API: {e}")
        return []

def run_worker():
    sparkhub_db.init_and_migrate_db()
    
    while True:
        try:
            with sparkhub_db.get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT id, content FROM memories 
                    WHERE id NOT IN (SELECT memory_id FROM memories_embeddings)
                    AND is_sensitive = FALSE
                    LIMIT ?
                """, (BATCH_SIZE,))
                rows = cur.fetchall()
                
            if not rows:
                print("[EMBED WORKER] Banco 100% vetorizado. Aguardando novas memorias...")
                time.sleep(30)
                continue
                
            print(f"[EMBED WORKER] Processando lote de {len(rows)} memorias...")
            
            for row_id, content in rows:
                print(f"  -> Gerando vetor para ID {row_id}...")
                vec = get_embedding(content)
                if vec:
                    vec_json = json.dumps(vec)
                    with sparkhub_db.get_db_connection() as conn:
                        conn.execute("INSERT OR REPLACE INTO memories_embeddings (memory_id, embedding) VALUES (?, ?)", (row_id, vec_json))
                        conn.commit()
                else:
                    print(f"  -> Falha ao obter vetor para ID {row_id}")
                
                # Delay agressivo para evitar Rate Limit (HTTP 429) na camada gratuita
                time.sleep(1.5)
                
            time.sleep(DELAY_BETWEEN_BATCHES)
            
        except Exception as e:
            print(f"[EMBED WORKER] Erro fatal no loop: {e}")
            time.sleep(10)

if __name__ == "__main__":
    print(f"=== SPARKHUB EMBED WORKER v3.0 ===")
    print(f"Modelo Ativo: {EMBEDDING_MODEL}")
    run_worker()
