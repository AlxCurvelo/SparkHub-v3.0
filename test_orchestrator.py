import os
import requests
import json
import time
from dotenv import load_dotenv

load_dotenv("D:\\SparkHub\\.env", override=True)
token = os.environ.get("SPARKHUB_API_TOKEN", "")

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
    "User-Agent": "TestClient"
}

payload = {
    "jsonrpc": "2.0",
    "id": "1",
    "method": "tools/call",
    "params": {
        "name": "ask_ai",
        "arguments": {
            "model": "local",
            "prompt": "Responda apenas com a palavra 'teste'."
        }
    }
}

print("Chamada 1 (Deve ser normal):")
r1 = requests.post("http://127.0.0.1:8000/", json=payload, headers=headers)
print(r1.json())

print("\nChamada 2 (Deve ser deduplicada / Cache HIT):")
r2 = requests.post("http://127.0.0.1:8000/", json=payload, headers=headers)
print(r2.json())

print("\nAguardando 6s para expirar janela de cache...")
time.sleep(6)

print("\nChamada 3 (Deve ser normal novamente):")
r3 = requests.post("http://127.0.0.1:8000/", json=payload, headers=headers)
print(r3.json())
