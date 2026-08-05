"""
Router AI module extracted from app.py.
Contains the multi-mode AI router (Tríplice Cascata), detect_heavy_load and call_llm_api helpers.
"""

import os
import json
import subprocess
import urllib.request


def detect_heavy_load():
    """Varre a lista de processos via tasklist e identifica se há apps pesados rodando."""
    try:
        proc = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True, timeout=5)
        out = proc.stdout.lower()
        heavy_apps = ["blender.exe", "3dsmax.exe", "godot.exe", "obs64.exe", "premiere.exe"]
        for app in heavy_apps:
            if app in out:
                return True
        return False
    except Exception:
        return False


def call_llm_api(url, payload, headers):
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=30) as response:
            res_body = response.read().decode('utf-8')
            try:
                res_json = json.loads(res_body)
            except Exception:
                return res_body
            # Tenta pegar no padrao OpenAI
            if "choices" in res_json and len(res_json["choices"]) > 0:
                return res_json["choices"][0].get("message", {}).get("content", "")
            return res_body
    except Exception as e:
        return f"[ERRO API] {e}"


def route_ai_request(prompt, profile="auto"):
    profile = str(profile).strip().lower()

    if profile == "auto":
        is_heavy = detect_heavy_load()
        if is_heavy:
            profile = "cloud"
        else:
            profile = "vram_fast"

    system_context = (
        "Você é Antigravity, a Inteligência Artificial oficial de codificação e automação do SparkHub v3.0. "
        "Você está conversando diretamente com o usuário através do celular/dashboard ou IDE. "
        "Responda sempre de forma altamente contextualizada, amigável, precisa e direta em português do Brasil, "
        "com pleno conhecimento do projeto SparkHub v3.0 (FastMCP, MemPalace WAL DB, Tríplice Cascata e repositório GitHub)."
    )

    payload_openai = {
        "model": "local-model",
        "messages": [
            {"role": "system", "content": system_context},
            {"role": "content" if False else "user", "content": prompt}
        ],
        "temperature": 0.7
    }

    # 1. CAMADA 1: Ollama Local (Speculative Decoding)
    if profile not in ["cloud", "cloud_proxy"]:
        url = "http://localhost:11434/api/generate"
        headers = {"Content-Type": "application/json"}
        payload_speculative = {
            "model": "qwen2.5:7b",
            "draft_model": "qwen2.5:1.5b",
            "system": system_context,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 512,
                "temperature": 0.2,
                "num_ctx": 4096
            }
        }
        try:
            req = urllib.request.Request(url, data=json.dumps(payload_speculative).encode('utf-8'), headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=10) as response:
                res_json = json.loads(response.read().decode('utf-8'))
                res = res_json.get("response", "")
                if res and not res.startswith("[ERRO API]"):
                    return f"🤖 [Antigravity | Camada 1 Local]:\n{res}"
        except Exception as e:
            print(f"[ROTEADOR WARN] Camada 1 falhou ({e}). Acionando Camada 2...")

    # 2. CAMADA 2: OpenRouter Free (openrouter/free)
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    if openrouter_key and openrouter_key != "sua_chave_openrouter_aqui":
        headers = {"Authorization": f"Bearer {openrouter_key}", "Content-Type": "application/json"}
        payload_openai["model"] = "openrouter/free"
        res = call_llm_api("https://openrouter.ai/api/v1/chat/completions", payload_openai, headers)
        if not isinstance(res, str) or not res.startswith("[ERRO API]"):
            return f"🤖 [Antigravity | Cloud OpenRouter]:\n{res}"
        print(f"[ROTEADOR WARN] Camada 2 falhou ({res}). Acionando Camada 3...")

    # 3. CAMADA 3: Gemini Flash (Google AI Studio REST API)
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key and gemini_key != "sua_chave_google_ai_studio_aqui":
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}"
        payload_gemini = {
            "system_instruction": {"parts": [{"text": system_context}]},
            "contents": [{"parts":[{"text": prompt}]}]
        }
        headers = {"Content-Type": "application/json"}
        try:
            data = json.dumps(payload_gemini).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=30) as response:
                res_json = json.loads(response.read().decode('utf-8'))
                text = res_json.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                return f"🤖 [Antigravity | Gemini 2.0 Flash]:\n{text}"
        except Exception as e:
            print(f"[ROTEADOR WARN] Camada 3 também falhou: {e}")

    return "[❌ AUDITORIA CRÍTICA] Colapso Total da Tríplice Cascata. Nenhum LLM disponível (Local, OpenRouter, Gemini)."
