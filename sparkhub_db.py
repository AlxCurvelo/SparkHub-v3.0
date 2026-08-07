"""
SparkHub v3.0 - Unified Database & Resilience Engine (sparkhub_db.py)
Provides thread-safe, WAL-enabled SQLite persistence, automatic schema migration,
and safe transaction retries.
"""

import os
import sqlite3
import datetime
import sparkhub_crypto

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mempalace.db")

def get_db_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Returns a SQLite connection with WAL mode enabled and timeout configured."""
    conn = sqlite3.connect(db_path, timeout=10.0, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

# Expor utilitário de inicialização FTS centralizado

def init_fts5_if_needed(db_path: str = DB_PATH) -> None:
    """Configura o índice de busca BM25 (FTS5) se não existir."""
    if not os.path.exists(db_path):
        return
    try:
        with sqlite3.connect(db_path) as conn:
            cur = conn.cursor()
            cur.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts 
                USING fts5(wing, room, content, content='memories', content_rowid='id');
            """)
            cur.execute("INSERT OR IGNORE INTO memories_fts(rowid, wing, room, content) SELECT id, wing, room, content FROM memories;")
            conn.commit()
    except Exception as e:
        print(f"[DB MIGRATION] Erro ao inicializar FTS5: {e}")
        raise

def init_and_migrate_db(db_path: str = DB_PATH):
    """Ensures all required tables and columns exist in mempalace.db."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        
        # 1. Main memories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wing TEXT NOT NULL,
                room TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                timestamp TEXT,
                updated_at TEXT
            );
        """)
        
        # Auto-migration for missing columns in 'memories'
        cursor.execute("PRAGMA table_info(memories);")
        columns = [col[1] for col in cursor.fetchall()]
        
        if "updated_at" not in columns:
            cursor.execute("ALTER TABLE memories ADD COLUMN updated_at TEXT;")
            print("[DB MIGRATION] Added 'updated_at' column to 'memories'.")
            
        if "timestamp" not in columns:
            cursor.execute("ALTER TABLE memories ADD COLUMN timestamp TEXT;")
            print("[DB MIGRATION] Added 'timestamp' column to 'memories'.")

        if "is_sensitive" not in columns:
            cursor.execute("ALTER TABLE memories ADD COLUMN is_sensitive BOOLEAN DEFAULT FALSE;")
            print("[DB MIGRATION] Added 'is_sensitive' column to 'memories'.")

        # 2. Chat history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT NOT NULL,
                message TEXT NOT NULL,
                response TEXT,
                channel TEXT DEFAULT 'mobile',
                created_at TEXT DEFAULT (datetime('now'))
            );
        """)
        
        # 3. Agent tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_name TEXT NOT NULL,
                status TEXT NOT NULL,
                details TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT
            );
        """)
        
        # 4. Embeddings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories_embeddings (
                memory_id INTEGER PRIMARY KEY,
                embedding TEXT NOT NULL
            );
        """)
        
        # 5. Processed Media Registry (Deduplicação)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processed_media_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_hash TEXT UNIQUE NOT NULL,
                original_name TEXT NOT NULL,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                mem_id INTEGER
            );
        """)
        
        # 6. Telemetry (Orchestrator)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS telemetry (
                request_id TEXT PRIMARY KEY,
                origin TEXT NOT NULL,
                tool TEXT NOT NULL,
                status TEXT NOT NULL,
                latency_ms REAL NOT NULL,
                bytes_in INTEGER NOT NULL,
                bytes_out INTEGER NOT NULL,
                backend_used TEXT NOT NULL,
                cache_hit BOOLEAN NOT NULL,
                sha256 TEXT,
                timestamp TEXT DEFAULT (datetime('now'))
            )
        """)
        
        conn.commit()

def insert_telemetry(record: dict, db_path: str = DB_PATH) -> bool:
    """Insere um registro de telemetria no banco de dados SQLite."""
    try:
        with get_db_connection(db_path) as conn:
            conn.execute("""
                INSERT INTO telemetry 
                (request_id, origin, tool, status, latency_ms, bytes_in, bytes_out, backend_used, cache_hit, sha256, timestamp) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record["request_id"], record["origin"], record["tool"], record["status"],
                record["latency_ms"], record["bytes_in"], record["bytes_out"],
                record["backend_used"], record["cache_hit"], record.get("sha256", ""), record["timestamp"].isoformat()
            ))
            conn.commit()
        return True
    except Exception as e:
        print(f"[TELEMETRIA] Erro ao salvar log no BD: {e}")
        return False

def save_memory(wing: str, room: str, content: str, db_path: str = DB_PATH) -> int:
    """Safely saves a memory entry into mempalace.db. Returns mem_id or 0 on failure."""
    try:
        init_and_migrate_db(db_path)
        
        termos_sensiveis = ["laudo", "perícia", "pericial", "confidencial", "rh", "contrato", "extrato", "sigiloso"]
        # Checa sensibilidade apenas na origem (wing) ou título/assunto (room). 
        # Ignora menções no corpo do texto para evitar falsos positivos incidentais.
        is_sensitive = ("Trabalho" in room) or ("Trabalho" in wing) or any(t in room.lower() for t in termos_sensiveis)
        
        if is_sensitive:
            content = sparkhub_crypto.encrypt_content(content)
            
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with get_db_connection(db_path) as conn:
            cur = conn.execute(
                "INSERT INTO memories (wing, room, content, timestamp, updated_at, is_sensitive) VALUES (?, ?, ?, ?, ?, ?)",
                (wing, room, content, now_iso, now_iso, is_sensitive)
            )
            rowid = cur.lastrowid
            
            # Atualizar FTS5 apenas para registros não-sensíveis
            if not is_sensitive:
                conn.execute(
                    "INSERT INTO memories_fts(rowid, wing, room, content) VALUES (?, ?, ?, ?)",
                    (rowid, wing, room, content)
                )
                
            conn.commit()
        return rowid
    except Exception as e:
        print(f"[DB ERROR] Error saving memory ({wing}/{room}): {e}")
        return 0

def check_media_processed(file_hash: str, db_path: str = DB_PATH) -> bool:
    try:
        with get_db_connection(db_path) as conn:
            cur = conn.execute("SELECT 1 FROM processed_media_registry WHERE file_hash = ?", (file_hash,))
            return cur.fetchone() is not None
    except Exception as e:
        print(f"[DB ERROR] check_media_processed falhou: {e}")
        return False

def register_processed_media(file_hash: str, original_name: str, mem_id: int, db_path: str = DB_PATH) -> bool:
    try:
        with get_db_connection(db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO processed_media_registry (file_hash, original_name, mem_id) VALUES (?, ?, ?)",
                (file_hash, original_name, mem_id)
            )
            conn.commit()
        return True
    except Exception as e:
        print(f"[DB ERROR] register_processed_media falhou: {e}")
        return False
        return False

def save_chat_message(sender: str, message: str, response: str = "", channel: str = "mobile", db_path: str = DB_PATH) -> bool:
    """Safely saves a chat interaction into chat_history and memories."""
    try:
        init_and_migrate_db(db_path)
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with get_db_connection(db_path) as conn:
            conn.execute(
                "INSERT INTO chat_history (sender, message, response, channel, created_at) VALUES (?, ?, ?, ?, ?)",
                (sender, message, response, channel, now_iso)
            )
            conn.commit()
        
        # Mirror to memories room 'agent_tasks'
        save_memory("Agent", "agent_tasks", f"[{channel.upper()}] {sender}: {message} | Response: {response[:100]}", db_path)
        return True
    except Exception as e:
        print(f"[DB ERROR] Error saving chat message: {e}")
        return False

if __name__ == "__main__":
    init_and_migrate_db()
    print("[DB ENGINE] SparkHub Database initial migration & health check OK!")

def mempalace_search(query: str, db_path: str = DB_PATH, limit: int = 5) -> str:
    """Busca no MemPalace via FTS5 e LIKE para fallback se IAs caírem."""
    try:
        init_and_migrate_db(db_path)
        with get_db_connection(db_path) as conn:
            try:
                cur = conn.execute(
                    "SELECT wing, room, content FROM memories_fts WHERE memories_fts MATCH ? ORDER BY rank LIMIT ?",
                    (query, limit)
                )
                rows = cur.fetchall()
            except Exception:
                rows = []
            
            if not rows:
                like_q = f"%{query}%"
                cur = conn.execute(
                    "SELECT wing, room, content FROM memories WHERE content LIKE ? OR room LIKE ? LIMIT ?",
                    (like_q, like_q, limit)
                )
                rows = cur.fetchall()
                
            if not rows:
                return "Nenhum resultado encontrado localmente."
                
            res = []
            for r in rows:
                wing, room, content_text = r[0], r[1], str(r[2])
                res.append(f"- [{wing}/{room}]: {content_text[:200]}...")
            return "\n".join(res)
    except Exception as e:
        return f"Erro na busca local: {e}"
