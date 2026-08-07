import os
from dotenv import load_dotenv
import router_ai

def test_failover():
    # Carrega o .env real ignorando o ambiente global corrompido
    load_dotenv(override=True)
    
    # Exibe o prefixo e sufixo da chave Gemini para provar que está configurada
    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    print(f"1. GEMINI_API_KEY carregada: Prefixo={gemini_key[:8]}... Sufixo=...{gemini_key[-6:]}")
    
    # Simula a queda da Camada 2 (OpenRouter)
    print("2. Simulando queda da Camada 2 (Invalidando OPENROUTER_API_KEY temporariamente)...")
    os.environ["OPENROUTER_API_KEY"] = "token_invalido_simulando_queda"
    
    # Simula a queda da Camada 3 (DeepSeek)
    print("3. Simulando queda da Camada 3 (Invalidando DEEPSEEK_API_KEY temporariamente)...")
    os.environ["DEEPSEEK_API_KEY"] = "token_invalido_simulando_queda"
    
    # A Camada 1 (Local) já falhará porque o Ollama não está rodando neste ambiente de teste
    
    print("4. Fazendo pergunta simples para a Cascata...\n")
    
    # Chama o roteador
    resposta = router_ai.route_ai_request("Responda em uma frase curta: qual o seu nome e de qual modelo você está respondendo agora?")
    
    print("=== RESULTADO BRUTO DO ROTEADOR ===")
    print(resposta)
    print("===================================")

if __name__ == "__main__":
    test_failover()
