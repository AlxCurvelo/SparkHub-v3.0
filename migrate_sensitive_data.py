import os
import sqlite3
import sparkhub_crypto
from sparkhub_paths import get_path

# Mesmos termos do ingestao_drive.py
TERMOS_SENSIVEIS = ["laudo", "perícia", "pericial", "confidencial", "rh", "contrato", "extrato", "sigiloso"]

def is_text_sensitive(text: str) -> bool:
    if not text:
        return False
    text_lower = text.lower()
    return any(t in text_lower for t in TERMOS_SENSIVEIS)

def migrate_old_memories():
    db_path = get_path("mempalace.db")
    print(f"=== INICIANDO MIGRAÇÃO RETROATIVA DE DADOS SENSÍVEIS ===")
    
    # Garantir que o cofre está destrancado para podermos criptografar
    if not sparkhub_crypto.is_vault_unlocked():
        print("[ERRO] O cofre está trancado. É necessário o .master_key ativo para criptografar.")
        return
        
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Buscar registros que ainda não foram marcados como sensíveis (ou são NULL)
    cursor.execute("SELECT id, wing, room, content FROM memories WHERE is_sensitive IS NULL OR is_sensitive = 0")
    rows = cursor.fetchall()
    
    migrated_count = 0
    for row in rows:
        row_id = row["id"]
        wing = row["wing"]
        room = row["room"]
        content = row["content"]
        
        # Pula se o conteúdo já parecer criptografado por acidente
        if content and content.startswith("gAAAAAB"):
            continue
            
        # Avaliar sensibilidade:
        # Se for da conta de "Trabalho" ou se contiver termos sensíveis
        sensitive = False
        if wing == "Trabalho" or is_text_sensitive(room) or is_text_sensitive(content):
            sensitive = True
            
        if sensitive:
            print(f"[MIGRAÇÃO] Registro #{row_id} detectado como sensível (Origem: {wing} -> {room}). Criptografando...")
            
            # Criptografar
            enc_content = sparkhub_crypto.encrypt_content(content)
            
            # Atualizar registro base
            cursor.execute("UPDATE memories SET content = ?, is_sensitive = 1 WHERE id = ?", (enc_content, row_id))
            
            # Remover do FTS para não vazar
            cursor.execute("DELETE FROM memories_fts WHERE rowid = ?", (row_id,))
            
            migrated_count += 1
            
    conn.commit()
    conn.close()
    
    print(f"\n[SUCESSO] Migração concluída. {migrated_count} registros antigos foram criptografados retroativamente.")

if __name__ == "__main__":
    migrate_old_memories()
