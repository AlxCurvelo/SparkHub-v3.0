import os
import sqlite3
import pyotp
import time
import sparkhub_db
import sparkhub_crypto
from sparkhub_paths import get_path
import app

def test_crypto():
    master_key_path = get_path(".master_key")
    lock_file = get_path(".totp_lockout")
    
    print("=== INICIANDO BATERIA DE TESTES CRIPTOGRÁFICOS ===\n")
    
    # ---------------------------------------------------------
    # SETUP & TESTE 3: ROUND-TRIP COMPLETO (Gerar -> Gravar -> Ler)
    # ---------------------------------------------------------
    print("--- Teste 3 (Parte 1): Geração de Chave via TOTP ---")
    if os.path.exists(master_key_path):
        os.remove(master_key_path)
    if os.path.exists(lock_file):
        os.remove(lock_file)
        
    secret = sparkhub_crypto.get_totp_secret()
    totp = pyotp.TOTP(secret)
    valid_code = totp.now()
    
    res_unlock_success = app.mempalace_unlock(valid_code)
    if "desbloqueado" in res_unlock_success and os.path.exists(master_key_path):
        print("[PASS] Sistema aceitou código TOTP válido e gerou .master_key via DPAPI.")
    else:
        print(f"[FAIL] Sistema rejeitou código válido ou não gerou chave. Saída: {res_unlock_success}")
        return

    print("\n--- Teste 3 (Parte 2): Round-Trip Decriptografia ---")
    termo_sigiloso = "Este é um laudo médico confidencial e abs_exclusivo_teste."
    termo_publico = "Este é um texto normal de teste abs_exclusivo_pub."
    
    sparkhub_db.save_memory("Geral", "SalaComum", termo_publico, db_path=sparkhub_db.DB_PATH)
    sparkhub_db.save_memory("Geral", "RH", termo_sigiloso, db_path=sparkhub_db.DB_PATH)
    
    res_leitura_livre = app.mempalace_search("RH")
    if "abs_exclusivo_teste" in res_leitura_livre:
        print("[PASS] Dado sensível lido, decifrado e texto original intacto após gravação.")
    else:
        print(f"[FAIL] Decriptografia falhou ou dado corrompido! Saída: {res_leitura_livre}")

    # ---------------------------------------------------------
    # TRANCA O COFRE PARA OS PRÓXIMOS TESTES
    # ---------------------------------------------------------
    print("\n[SETUP] Trancando o cofre (renomeando .master_key para simular máquina não autorizada)...")
    os.rename(str(master_key_path), str(master_key_path) + ".bak")

    # ---------------------------------------------------------
    # TESTE 1: LEITURA BLOQUEADA
    # ---------------------------------------------------------
    print("\n--- Teste 1: Acesso Sensível sem Máquina Registrada ---")
    res_sensivel = app.mempalace_search("RH")
    if "[CONTEÚDO PROTEGIDO POR CRIPTOGRAFIA TOTP]" in res_sensivel:
        print("[PASS] Sistema bloqueou corretamente a leitura do dado sensível.")
    else:
        print(f"[FAIL] Vazamento detectado ou dado ausente! Saída: {res_sensivel}")

    # ---------------------------------------------------------
    # NOVO TESTE: EXCLUSÃO DO FTS
    # ---------------------------------------------------------
    print("\n--- Teste Extra: Exclusão do FTS (Busca por conteúdo sensível enquanto trancado) ---")
    # Tenta buscar pela palavra que só existe dentro do dado sensível
    res_fts = app.mempalace_search("abs_exclusivo_teste")
    if "Nenhuma memória encontrada" in res_fts:
        print("[PASS] Palavra sensível não vazou pelo índice de busca (FTS/LIKE).")
    else:
        print(f"[FAIL] O termo sensível foi encontrado no banco trancado! Saída: {res_fts}")

    # ---------------------------------------------------------
    # TESTE 4: SANDBOX NÃO-SENSÍVEL
    # ---------------------------------------------------------
    print("\n--- Teste 4: Sandbox Não-Sensível (Híbrido) ---")
    res_normal = app.mempalace_search("texto normal")
    if termo_publico in res_normal and "[CONTEÚDO PROTEGIDO" not in res_normal:
        print("[PASS] Leitura de dado não-sensível funcionou perfeitamente mesmo com o cofre trancado.")
    else:
        print(f"[FAIL] Falha ao ler dado público! Saída: {res_normal}")

    # ---------------------------------------------------------
    # TESTE 2 & NOVO TESTE: RATE LIMIT ATÉ O FIM
    # ---------------------------------------------------------
    print("\n--- Teste 2 & Rate Limit: Forçando exaustão (5 erros) ---")
    for i in range(1, 6):
        res_fail = app.mempalace_unlock("000000")
        if "Falha" in res_fail or "Bloqueio" in res_fail:
            print(f"[PASS] Tentativa {i}/5 rejeitada corretamente.")
        else:
            print(f"[FAIL] Sistema aceitou código inválido na tentativa {i}! Saída: {res_fail}")
            
    print("\n--- Teste: 6ª tentativa com código CORRETO ---")
    valid_code_2 = totp.now()
    res_lockout = app.mempalace_unlock(valid_code_2)
    if "Bloqueio de Segurança" in res_lockout or "Muitas tentativas falhas" in res_lockout:
        print("[PASS] Rate Limit funcionou! A 6ª tentativa foi bloqueada mesmo com o código correto.")
    else:
        print(f"[FAIL] O sistema permitiu o desbloqueio ignorando o Rate Limit! Saída: {res_lockout}")

    # Cleanup
    os.rename(str(master_key_path) + ".bak", str(master_key_path))
    if os.path.exists(lock_file):
        os.remove(lock_file)
        
    print("\n=== BATERIA CONCLUÍDA ===")

if __name__ == "__main__":
    test_crypto()
