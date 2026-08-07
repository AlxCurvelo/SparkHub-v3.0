import os
from dotenv import load_dotenv
import router_ai

def test_layer2():
    load_dotenv(override=True)
    
    # Exibe o sufixo da chave OpenRouter
    or_key = os.environ.get("OPENROUTER_API_KEY", "")
    print(f"1. OPENROUTER_API_KEY carregada: Sufixo=...{or_key[-10:] if or_key else 'AUSENTE'}")
    
    # A Camada 1 (Local) já falhará porque o Ollama não está rodando neste ambiente de teste
    print("2. O Ollama (Camada 1) está desligado.")
    
    print("3. Fazendo pergunta simples para testar a Camada 2 (OpenRouter)...\n")
    
    # Chama o roteador
    resposta = router_ai.route_ai_request("Responda em uma frase curta: qual o seu nome e de qual modelo você está respondendo agora?")
    
    print("=== RESULTADO BRUTO DO ROTEADOR ===")
    print(resposta)
    print("===================================")

if __name__ == "__main__":
    test_layer2()
