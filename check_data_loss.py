import sqlite3
import sparkhub_crypto
from sparkhub_paths import get_path

def test_data_loss():
    db_path = get_path("mempalace.db")
    
    print("=== VERIFICAÇÃO DE PERDA DE DADOS ===")
    
    # Certifique-se de que o cofre está destrancado com a chave atual
    if not sparkhub_crypto.is_vault_unlocked():
        print("[ERRO] Cofre trancado. Teste não pode continuar.")
        return
        
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Testa o laudo original (ID 97)
    cursor.execute("SELECT id, content FROM memories WHERE id = 97")
    row = cursor.fetchone()
    if row:
        print(f"\nTentando decifrar Registro #{row['id']} (Laudo Pericial):")
        decrypted = sparkhub_crypto.decrypt_content(row['content'])
        if decrypted.startswith("[ERRO"):
            print(f"-> [FALHA CRÍTICA] Dado irrecuperável: {decrypted}")
        else:
            print(f"-> [SUCESSO] Dado recuperado: {decrypted[:50]}...")
    else:
        print("\nRegistro #97 não encontrado.")
        
    # Testa um dos falsos positivos (ex: ID 354)
    cursor.execute("SELECT id, content FROM memories WHERE id = 354")
    row = cursor.fetchone()
    if row:
        print(f"\nTentando decifrar Registro #{row['id']} (Falso Positivo):")
        decrypted = sparkhub_crypto.decrypt_content(row['content'])
        if decrypted.startswith("[ERRO"):
            print(f"-> [FALHA CRÍTICA] Dado irrecuperável: {decrypted}")
        else:
            print(f"-> [SUCESSO] Dado recuperado: {decrypted[:50]}...")
            
    conn.close()

if __name__ == "__main__":
    test_data_loss()
