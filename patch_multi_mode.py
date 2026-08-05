import re

from sparkhub_paths import get_path

def main():
    app_path = get_path('app.py')
    with open(app_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Imports
    if 'import urllib.request' not in content:
        content = content.replace('import sys', 'import sys\nimport urllib.request\nimport urllib.error')

    # 2. Add Multi-Mode Logic
    multi_mode_code = '''
# =========================================================
# ROTEADOR MULTI-MODE (SPARKHUB AI ROUTER)
# =========================================================
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
            res_json = json.loads(res_body)
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
            
    payload_openai = {
        "model": "local-model", # ignorado por muitos backends locais
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    
    if profile == "cloud" or profile == "cloud_proxy":
        # Tenta Groq primeiro
        groq_key = os.environ.get("GROQ_API_KEY")
        if groq_key:
            headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
            payload_openai["model"] = "llama3-8b-8192"
            res = call_llm_api("https://api.groq.com/openai/v1/chat/completions", payload_openai, headers)
            return f"[☁️ CLOUD_PROXY: Groq]\\n{res}"
            
        # Fallback Gemini (formato nativo Gemini)
        gemini_key = os.environ.get("GEMINI_API_KEY")
        if gemini_key:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
            payload_gemini = {"contents": [{"parts":[{"text": prompt}]}]}
            headers = {"Content-Type": "application/json"}
            try:
                data = json.dumps(payload_gemini).encode('utf-8')
                req = urllib.request.Request(url, data=data, headers=headers, method='POST')
                with urllib.request.urlopen(req, timeout=30) as response:
                    res_json = json.loads(response.read().decode('utf-8'))
                    text = res_json.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    return f"[☁️ CLOUD_PROXY: Gemini]\\n{text}"
            except Exception as e:
                return f"[ERRO CLOUD GEMINI] {e}"
        
        return "[❌ AUDITORIA] Nenhuma API Key da nuvem (GROQ_API_KEY / GEMINI_API_KEY) foi encontrada no ambiente. Roteamento falhou."

    elif profile == "cpu" or profile == "cpu_silent":
        # Simulando endpoint local para CPU
        url = "http://localhost:11434/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        res = call_llm_api(url, payload_openai, headers)
        return f"[🧠 CPU_SILENT: Localhost]\\n{res}"

    elif profile == "hybrid":
        url = "http://localhost:1234/v1/chat/completions" # Exemplo LM Studio
        headers = {"Content-Type": "application/json"}
        res = call_llm_api(url, payload_openai, headers)
        return f"[⚙️ HYBRID: Localhost]\\n{res}"

    else: # VRAM_FAST default
        url = "http://localhost:11434/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        res = call_llm_api(url, payload_openai, headers)
        return f"[🚀 VRAM_FAST: Localhost]\\n{res}"

'''
    if 'def route_ai_request' not in content:
        target = 'def proactive_memory_check'
        content = content.replace(target, multi_mode_code + target)

    # 3. Add to MCP_TOOLS
    tool_def = '''    {
        "name": "ask_ai",
        "description": "Roteador Multi-Mode: Processa perguntas ou analises delegando para GPUs locais ou Nuvem com base no peso do sistema.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Texto da solicitação"},
                "profile": {"type": "string", "description": "Perfil de execucao: auto, vram_fast, hybrid, cpu_silent, cloud_proxy (default: auto)"}
            },
            "required": ["prompt"]
        }
    },
    {'''
    if '"name": "ask_ai"' not in content:
        content = content.replace('    {\n        "name": "find_app",', tool_def + '\n        "name": "find_app",')

    # 4. Add to execute_tool
    exec_block = '''
    if name == "ask_ai":
        prompt = args.get("prompt", "")
        profile = args.get("profile", "auto")
        update_state("ask_ai", app_name=profile)
        res = route_ai_request(prompt, profile)
        return finalize(res)

    if name == "find_app":'''
    if 'name == "ask_ai":' not in content:
        content = content.replace('    if name == "find_app":', exec_block)

    # 5. Update CLI argparse
    if '--profile' not in content:
        content = content.replace(
            'parser.add_argument("args", nargs="*", help="Argumentos da ferramenta em formato chave=valor ou string direta")',
            'parser.add_argument("args", nargs="*", help="Argumentos da ferramenta em formato chave=valor ou string direta")\n    parser.add_argument("--profile", default="auto", help="Perfil do Multi-Mode para ask_ai (auto, cloud, vram_fast, etc)")'
        )
        content = content.replace(
            'tool_kwargs[k] = v',
            'tool_kwargs[k] = v\n        if cli_args.profile and tool_name == "ask_ai":\n            tool_kwargs["profile"] = cli_args.profile'
        )

    with open(app_path, 'w', encoding='utf-8') as f:
        f.write(content)
        print("SparkHub Multi-Mode (Roteador de Perfis) injetado com sucesso no app.py")

if __name__ == "__main__":
    main()
