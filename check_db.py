import sqlite3
conn = sqlite3.connect(r'D:\SparkHub\mempalace.db')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("TABELAS:", [r[0] for r in cur.fetchall()])
try:
    cur.execute("SELECT * FROM memories ORDER BY rowid DESC LIMIT 5")
    rows = cur.fetchall()
    print(f"\nULTIMAS {len(rows)} MEMORIES:")
    for r in rows:
        print(r)
except Exception as e:
    print(f"Erro memories: {e}")
try:
    cur.execute("SELECT * FROM chat_history ORDER BY rowid DESC LIMIT 5")
    rows = cur.fetchall()
    print(f"\nULTIMO CHAT:")
    for r in rows:
        print(r)
except Exception as e:
    print(f"Sem chat_history: {e}")
conn.close()
