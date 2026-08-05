import sys
import app

print("=== TESTE DA TRÍPLICE CASCATA (Roteador Multi-Mode) ===")

print("\n1. Teste: Rota Cloud Forçada (Testa OpenRouter e Gemini)")
response_cloud = app.route_ai_request("Qual o capital da França?", profile="cloud")
print("Resposta:\n", response_cloud)

print("\n2. Teste: Rota VRAM_FAST Forçada (Testa Ollama)")
response_local = app.route_ai_request("Resumo de 5 palavras sobre IA.", profile="vram_fast")
print("Resposta:\n", response_local)
