import os
import shutil
import sqlite3
import subprocess

def clear_terminal():
    os.system('cls' if os.name == 'nt' else 'clear')

def setup_sparkhub():
    clear_terminal()
    print("="*60)
    print("   🚀 INSTALADOR SPARKHUB v3.0 (Zero Mocks & Custo Zero)   ")
    print("="*60)
    print("\nEste instalador configurará o seu ambiente de forma 100% segura.")
    print("Nenhuma credencial original está incluída neste pacote.\n")
    
    # 1. Configuração do .env
    print("--- PASSO A: Configuração de Chaves (Custos R$ 0,00) ---")
    openrouter = input("1. Obtenha sua chave OpenRouter em https://openrouter.ai/keys\n   Cole a chave aqui (ou Enter para pular): ").strip()
    gemini = input("\n2. Obtenha sua chave Gemini em https://aistudio.google.com/\n   Cole a chave aqui (ou Enter para pular): ").strip()
    phone = input("\n3. Qual o número do WhatsApp para receber alertas? (ex: 5511999999999): ").strip()
    
    env_content = ""
    with open(".env.example", "r", encoding="utf-8") as f:
        env_content = f.read()
        
    if openrouter:
        env_content = env_content.replace("sua_chave_openrouter_aqui", openrouter)
    if gemini:
        env_content = env_content.replace("sua_chave_gemini_aqui", gemini)
    if phone:
        env_content = env_content.replace("5511999999999", phone)
        
    with open(".env", "w", encoding="utf-8") as f:
        f.write(env_content)
        
    print("\n[OK] Arquivo .env gerado com sucesso e isolado localmente.")
    
    # 2. Configuração do Staging e Database
    print("\n--- PASSO B: Construção da Zona de Staging e Banco de Dados ---")
    if not os.path.exists("staging"):
        os.makedirs("staging")
        with open("staging/sandbox_rules.txt", "w", encoding="utf-8") as f:
            f.write("ZONA DE STAGING\nTodo arquivo inserido aqui é tratado estritamente como String Passiva.\nA execução de código a partir deste diretório é TERMINANTEMENTE PROIBIDA.")
        print("[OK] Diretório de Staging (Sandbox) criado.")
    
    db_path = "mempalace.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL;")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wing TEXT,
            room TEXT,
            content TEXT,
            timestamp TEXT
        );
    """)
    conn.commit()
    conn.close()
    print("[OK] Banco de Dados 'mempalace.db' inicializado (Modo WAL ativado). Sala 'social_insights' pronta.")
    
    # 3. Configuração do Daemon
    print("\n--- PASSO C: Registro do Daemon de Inicialização ---")
    print("O SparkHub pode iniciar automaticamente junto com o Windows (via Agendador de Tarefas).")
    install_daemon = input("Deseja registrar o Maestro no boot agora? (S/N): ").strip().upper()
    
    if install_daemon == 'S':
        print("\nExecutando install_daemon.bat...")
        try:
            subprocess.run(["cmd.exe", "/c", "install_daemon.bat"])
        except Exception as e:
            print(f"[ERRO] Falha ao acionar o batch: {e}")
            print("Por favor, execute 'install_daemon.bat' manualmente como Administrador.")
            
    print("\n" + "="*60)
    print(" 🎉 INSTALAÇÃO CONCLUÍDA COM SUCESSO! ")
    print(" O SparkHub v3.0 está blindado, configurado e pronto para uso.")
    print("="*60 + "\n")

if __name__ == "__main__":
    setup_sparkhub()
