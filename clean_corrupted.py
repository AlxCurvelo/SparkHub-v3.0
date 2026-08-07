import os
import shutil
import sqlite3
from sparkhub_paths import get_path

IDS_TO_DELETE = [
    85, 97, 109, 125, 145, 182, 183, 190, 191, 192, 
    193, 194, 195, 200, 205, 206, 210, 213, 214, 215, 
    216, 222, 223, 231, 238, 246, 247, 249, 250, 253, 
    269, 291, 302, 354, 355
]

def clean_database():
    db_path = get_path("mempalace.db")
    bak_path = get_path("mempalace.db.bak")
    
    # Passo 1: Backup
    shutil.copy2(db_path, bak_path)
    print(f"=== PASSO 1: BACKUP ===")
    print(f"Banco copiado para: {bak_path}")
    
    # Passo 2: Contagem antes
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM memories")
    count_before = cursor.fetchone()[0]
    
    # Passo 3: Delete
    print(f"\n=== PASSO 2: DELEÇÃO DOS CORROMPIDOS ===")
    placeholders = ",".join("?" * len(IDS_TO_DELETE))
    cursor.execute(f"DELETE FROM memories WHERE id IN ({placeholders})", IDS_TO_DELETE)
    deleted_count = cursor.rowcount
    conn.commit()
    
    # Passo 4: Contagem depois
    cursor.execute("SELECT COUNT(*) FROM memories")
    count_after = cursor.fetchone()[0]
    
    print(f"Total de registros antes : {count_before}")
    print(f"Registros deletados      : {deleted_count}")
    print(f"Total de registros depois: {count_after}")
    
    if count_before - count_after == len(IDS_TO_DELETE):
        print("[PASS] Contagem caiu exatamente 35 registros.")
    else:
        print("[ERRO] A contagem de deleção não bateu com o esperado!")
        
    conn.close()

if __name__ == "__main__":
    clean_database()
