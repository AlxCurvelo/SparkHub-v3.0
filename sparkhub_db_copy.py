"""
SparkHub v3.0 - Unified Database & Resilience Engine (sparkhub_db.py)
Provides thread-safe, WAL-enabled SQLite persistence, automatic schema migration,
and safe transaction retries.
"""

import os
import sqlite3
import datetime

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
        
        conn.commit()

def save_memory(wing: str, room: str, content: str, db_path: str = DB_PATH) -> bool:
    """Safely saves a memory entry into mempalace.db."""
    try:
        init_and_migrate_db(db_path)
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with get_db_connection(db_path) as conn:
            conn.execute(
                "INSERT INTO memories (wing, room, content, timestamp, updated_at) VALUES (?, ?, ?, ?, ?)",
                (wing, room, content, now_iso, now_iso)
            )
            conn.commit()
        return True
    except Exception as e:
        print(f"[DB ERROR] Error saving memory ({wing}/{room}): {e}")
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
