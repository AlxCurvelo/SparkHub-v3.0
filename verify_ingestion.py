import sqlite3
import sparkhub_crypto
from sparkhub_paths import get_path

def verify_new_ingestion():
    db_path = get_path("mempalace.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("=== VERIFICAÇÃO PÓS-INGESTÃO ===\n")
    
    # 1. Verificar o laudo
    cursor.execute("SELECT id, wing, room, content, is_sensitive FROM memories WHERE room LIKE '%laudo%' OR content LIKE '%laudo%' OR content LIKE 'gAAAAAB%' ORDER BY id DESC LIMIT 5")
    rows = cursor.fetchall()
    
    encontrou_laudo = False
    for row in rows:
        if row["is_sensitive"] == 1:
            encontrou_laudo = True
            print(f"[LAUDO - SENSÍVEL] ID #{row['id']} | Origem: {row['room']}")
            print(f"-> is_sensitive: {row['is_sensitive']}")
            print(f"-> Conteúdo cifrado? {'SIM (gAAAAA...)' if row['content'].startswith('gAAAAA') else 'NÃO'}")
            
    if not encontrou_laudo:
        print("[AVISO] Laudo sensível não encontrado nos últimos registros criptografados.")
        
    print("\n------------------------------------------------\n")
    
    # 2. Verificar o Guia Completo (falso positivo anterior)
    cursor.execute("SELECT id, wing, room, content, is_sensitive FROM memories WHERE content LIKE '%Guia Completo de Serviços%'")
    rows = cursor.fetchall()
    
    if rows:
        row = rows[-1]
        print(f"[GUIA - FALSO POSITIVO] ID #{row['id']} | Origem: {row['room']}")
        print(f"-> is_sensitive: {row['is_sensitive']}")
        print(f"-> Conteúdo cifrado? {'SIM' if row['content'].startswith('gAAAAA') else 'NÃO (Texto Puro)'}")
        if row["is_sensitive"] == 0:
            print(f"-> Snippet: {row['content'][:80].replace(chr(10), ' ')}...")
    else:
        print("[AVISO] Guia Completo não encontrado.")
        
    conn.close()

if __name__ == "__main__":
    verify_new_ingestion()
