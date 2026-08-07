import os
import json
import urllib.request
from dotenv import load_dotenv

load_dotenv(override=True)

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
CODE_MODEL = "poolside/laguna-xs-2.1:free"

def request_coding_assistance(prompt: str, context: str = "") -> str:
    """
    Aciona o Agente de Código (Laguna XS) via OpenRouter.
    Ideal para tarefas complexas de programação (Python, Godot, etc).
    """
    if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "sua_chave_openrouter_aqui":
        return "[ERRO] Chave OPENROUTER_API_KEY não configurada no .env."
        
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    full_prompt = prompt
    if context:
        full_prompt = f"Contexto do Código:\n{context}\n\nInstrução:\n{prompt}"
        
    payload = {
        "model": CODE_MODEL,
        "messages": [
            {"role": "system", "content": "Você é um Agente Especialista em Código (Poolside Laguna). Foque em eficiência, segurança e clean code."},
            {"role": "user", "content": full_prompt}
        ],
        "temperature": 0.2
    }
    
    try:
        req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=30) as response:
            res_body = response.read().decode('utf-8')
            res_json = json.loads(res_body)
            return res_json["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode('utf-8')
        print(f"[CODING AGENT WARN] HTTP Error {e.code}: {err_msg}")
        return f"[ERRO] Falha na API do OpenRouter: {e.code}"
    except Exception as e:
        print(f"[CODING AGENT WARN] Falha na execução: {e}")
        return f"[ERRO] Falha interna ao chamar o agente: {str(e)}"

if __name__ == "__main__":
    print("Testando Agente de Código (Poolside Laguna)...")
    res = request_coding_assistance("Escreva uma função simples em Python para inverter uma string.")
    print("\nResposta do Agente:\n")
    print(res)
