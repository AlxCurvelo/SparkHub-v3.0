"""
Router AI module extracted from app.py.
Contains the multi-mode AI router (Tríplice Cascata progressiva), detect_heavy_load and call_llm_api helpers.
"""

import os
import json
from sparkhub_logger import logger
import subprocess
import urllib.request
import workspace_agent

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
        with urllib.request.urlopen(req, timeout=120) as response:
            res_body = response.read().decode('utf-8')
            try:
                res_json = json.loads(res_body)
            except Exception:
                return {"content": res_body}
            
            # Formato OpenAI
            if "choices" in res_json and len(res_json["choices"]) > 0:
                return res_json["choices"][0].get("message", {"content": ""})
            
            # Formato Gemini
            if "candidates" in res_json and len(res_json["candidates"]) > 0:
                parts = res_json["candidates"][0].get("content", {}).get("parts", [])
                content = ""
                tool_calls = []
                for p in parts:
                    if "text" in p:
                        content += p["text"]
                    if "functionCall" in p:
                        fc = p["functionCall"]
                        tool_calls.append({
                            "id": "call_gemini",
                            "type": "function",
                            "function": {
                                "name": fc["name"],
                                "arguments": json.dumps(fc.get("args", {}))
                            }
                        })
                ans = {"content": content}
                if tool_calls:
                    ans["tool_calls"] = tool_calls
                return ans

            return {"content": res_body}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        return {"content": f"[ERRO API HTTP {e.code}] {error_body}"}
    except Exception as e:
        return {"content": f"[ERRO API] {e}"}

def _to_gemini_payload(openai_payload):
    gemini_payload = {
        "system_instruction": {"parts": []},
        "contents": [],
        "tools": [{"functionDeclarations": []}]
    }
    
    for msg in openai_payload.get("messages", []):
        role = msg.get("role")
        if role == "system":
            gemini_payload["system_instruction"]["parts"].append({"text": msg.get("content", "")})
        elif role == "user":
            gemini_payload["contents"].append({"role": "user", "parts": [{"text": msg.get("content", "")}]})
        elif role == "assistant":
            parts = []
            if msg.get("content"):
                parts.append({"text": msg.get("content")})
            for tc in msg.get("tool_calls", []):
                try:
                    args = json.loads(tc["function"]["arguments"])
                except Exception:
                    args = {}
                parts.append({
                    "functionCall": {
                        "name": tc["function"]["name"],
                        "args": args
                    }
                })
            if parts:
                gemini_payload["contents"].append({"role": "model", "parts": parts})
        elif role == "tool":
            gemini_payload["contents"].append({
                "role": "function",
                "parts": [{
                    "functionResponse": {
                        "name": msg.get("name"),
                        "response": {"result": msg.get("content")}
                    }
                }]
            })
            
    for tool in openai_payload.get("tools", []):
        fn = tool["function"]
        params = dict(fn.get("parameters", {}))
        if "type" in params:
            params["type"] = str(params["type"]).upper()
        if "properties" in params:
            new_props = {}
            for k, v in params["properties"].items():
                nv = dict(v)
                if "type" in nv:
                    nv["type"] = str(nv["type"]).upper()
                new_props[k] = nv
            params["properties"] = new_props
                    
        gemini_payload["tools"][0]["functionDeclarations"].append({
            "name": fn["name"],
            "description": fn["description"],
            "parameters": params
        })
        
    return gemini_payload


def _executar_com_tools(modelo_info, prompt, max_iter, system_context, payload_base):
    # Clona o payload inicial para não sujar o original
    payload = json.loads(json.dumps(payload_base))
    
    # Adiciona a system message se for formato OpenAI, se for Gemini será mapeado no helper
    payload["messages"] = [
        {"role": "system", "content": system_context},
        {"role": "user", "content": prompt}
    ]
    
    url = modelo_info["url"]
    headers = modelo_info["headers"]
    
    if modelo_info["id"] != "gemini":
        payload["model"] = modelo_info["model_name"]
    
    api_error = False
    for _ in range(max_iter):
        
        req_payload = payload
        if modelo_info["id"] == "gemini":
            try:
                req_payload = _to_gemini_payload(payload)
            except Exception as e:
                import traceback
                logger.error(f"[CASCATA ERRO FATAL] Falha ao traduzir schema para Gemini:\n{traceback.format_exc()}")
                return None
            
        res_msg = call_llm_api(url, req_payload, headers)
        content = res_msg.get("content", "")
        
        if content and str(content).startswith("[ERRO API"):
            logger.error(f"[CASCATA] {modelo_info['id']} indisponível/erro: {content}. Subindo camada.")
            api_error = True
            break
            
        tool_calls = res_msg.get("tool_calls", [])
        if not tool_calls:
            if modelo_info["id"] == "ollama" and _ == 0:
                logger.info("[ROTEADOR] Ollama não retornou tool_calls. Modelo pode não suportar tools nativamente. Seguindo com resposta direta.")
            # Resposta final concluída
            if not content or not content.strip():
                # Conteúdo vazio = não concluiu
                break
            return content
            
        # Intercepta as chamadas de ferramenta
        payload["messages"].append(res_msg)
        for tc in tool_calls:
            tool_name = tc.get("function", {}).get("name")
            try:
                args = json.loads(tc.get("function", {}).get("arguments", "{}"))
            except Exception:
                args = {}
                
            tool_res = ""
            if tool_name == "search_gmail":
                logger.info(f"[ROTEADOR] Tool Call Interceptado ({modelo_info['id']}): search_gmail {args}")
                tool_res = str(workspace_agent.search_gmail(args.get("query", "")))
            elif tool_name == "search_drive_docs":
                logger.info(f"[ROTEADOR] Tool Call Interceptado ({modelo_info['id']}): search_drive_docs {args}")
                tool_res = str(workspace_agent.search_drive_docs(args.get("query", "")))
            else:
                tool_res = "Tool desconhecida."
                
            payload["messages"].append({
                "role": "tool",
                "tool_call_id": tc.get("id", "call_gemini"),
                "name": tool_name,
                "content": tool_res
            })
            
    if not api_error:
        msg = f"Camada {modelo_info['id']} esgotou {max_iter} iterações sem resposta. Avançando."
        logger.warning(f"[CASCATA] {msg}")
        try:
            import sparkhub_ipc
            sparkhub_ipc.notify_ide_quadchannel("Fallback por Tool Calling", msg)
        except Exception:
            pass
    return None



def _chamar_modelo_sem_tools(modelo_info, prompt, system_context, payload_base):
    import json, urllib.request
    payload = json.loads(json.dumps(payload_base))
    
    # Adiciona a system message se for formato OpenAI
    payload["messages"] = [
        {"role": "system", "content": system_context},
        {"role": "user", "content": prompt}
    ]
    
    # Remove tools
    if "tools" in payload:
        del payload["tools"]
        
    url = modelo_info["url"]
    headers = modelo_info["headers"]
    
    if modelo_info["id"] != "gemini":
        payload["model"] = modelo_info["model_name"]
        
    req_payload = payload
    if modelo_info["id"] == "gemini":
        req_payload = _to_gemini_payload(payload)
        if "tools" in req_payload:
            del req_payload["tools"]

    req = urllib.request.Request(url, data=json.dumps(req_payload).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            resp_data = json.loads(response.read().decode("utf-8"))
            
            if modelo_info["id"] == "gemini":
                candidates = resp_data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    return "".join([p.get("text", "") for p in parts if "text" in p])
                return None
            else:
                choices = resp_data.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "")
                return None
    except Exception as e:
        logger.error(f"[CASCATA SEM TOOLS] {modelo_info['id']} indisponivel/erro: {e}")
        return None

def route_ai_request(prompt: str, profile: str = "auto") -> str:
    
    system_context = (
        "Você é Antigravity, a Inteligência Artificial oficial de codificação e automação do SparkHub v3.0. "
        "Você está conversando diretamente com o usuário através do celular/dashboard ou IDE. "
        "Responda sempre de forma altamente contextualizada, amigável, precisa e direta em português do Brasil, "
        "com pleno conhecimento do projeto SparkHub v3.0 (FastMCP, MemPalace WAL DB, Tríplice Cascata e repositório GitHub)."
    )

    payload_base = {
        "model": "local-model",
        "messages": [
            {"role": "system", "content": system_context},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3
    }
    camadas = []
    
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")
    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    
    # Camada 1: Ollama Local
    camadas.append({
        "id": "ollama",
        "url": "http://127.0.0.1:11434/v1/chat/completions",
        "headers": {"Content-Type": "application/json"},
        "model_name": "qwen2.5:7b",
        "max_iter": 3,
        "prefix": "Antigravity | Edge Local"
    })
    
    # Camada 2: OpenRouter Fast
    if openrouter_key and openrouter_key != "sua_chave_openrouter_aqui":
        camadas.append({
            "id": "openrouter",
            "url": "https://openrouter.ai/api/v1/chat/completions",
            "headers": {"Authorization": f"Bearer {openrouter_key}", "Content-Type": "application/json"},
            "model_name": "poolside/laguna-xs-2.1:free",
            "max_iter": 3,
            "prefix": "Antigravity | Cloud OpenRouter"
        })
        
    # Camada 3: OpenRouter Heavy (Laguna S 2.1 - 100% Free)
    if openrouter_key and openrouter_key != "sua_chave_openrouter_aqui":
        camadas.append({
            "id": "openrouter_heavy",
            "url": "https://openrouter.ai/api/v1/chat/completions",
            "headers": {"Authorization": f"Bearer {openrouter_key}", "Content-Type": "application/json"},
            "model_name": "poolside/laguna-s-2.1:free",
            "max_iter": 5,
            "prefix": "Antigravity | Cloud OpenRouter Heavy"
        })
        
    # Camada 4: Gemini Flash
    if gemini_key and gemini_key != "sua_chave_gemini_aqui":
        camadas.append({
            "id": "gemini",
            "url": f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}",
            "headers": {"Content-Type": "application/json"},
            "model_name": "gemini-2.0-flash",
            "max_iter": 7,
            "prefix": "Antigravity | Cloud Gemini"
        })

    # FASE 1: Busca Desacoplada (Search-Augmented Prompt)
    contexto = ""
    try:
        from sparkhub_search_agent import SearchAgent
        agent = SearchAgent()
        classificacao = agent.classificar(prompt)
        
        if classificacao.precisa_buscar:
            logger.info(f"[SEARCH AGENT] Realizando buscas via {classificacao.fontes}")
            resultados = agent.executar_buscas(classificacao.queries, classificacao.fontes)
            contexto = agent.formatar_contexto(resultados)
            logger.info(f"[SEARCH AGENT] Busca concluída.")
    except Exception as e:
        logger.warning(f"[SEARCH AGENT] Falhou, seguindo sem contexto: {e}")
    
    # FASE 2: Prompt enriquecido
    if contexto:
        prompt_enriquecido = f"{contexto}\n\n[PERGUNTA DO USUÁRIO]\n{prompt}"
    else:
        prompt_enriquecido = prompt

    # FASE 3: Cascata de LLMs sem tools
    for modelo in camadas:
        resposta = _chamar_modelo_sem_tools(modelo, prompt_enriquecido, system_context, payload_base)
        if resposta and resposta.strip():
            ans = f"🤖 [{modelo['prefix']}]:\n{resposta}"
            logger.info(f"[ROTEADOR SUCESSO] Resposta via {modelo['id']} (Tamanho: {len(ans)})")
            return ans
            
    # --- FALLBACK DO MEMPALACE ---
    logger.error("[ROTEADOR WARN] Colapso Total da Cascata. Acionando Fallback Local do MemPalace.")
    try:
        from sparkhub_db import mempalace_search
        local_res = mempalace_search(prompt)
        if local_res and "Nenhum resultado" not in local_res:
            ans = f"🤖 [Antigravity | Fallback Local]: Sem conexão com IAs. Aqui está o que encontrei diretamente no meu banco de memória:\n\n{local_res}"
            return ans
    except Exception as e:
        logger.error(f"[CASCATA ERRO FATAL] Falha no fallback local: {e}")

    return "⚠️ [❌ AUDITORIA CRÍTICA] Colapso Total da Cascata. Nenhum modelo conseguiu responder e a busca local não retornou resultados (ou falhou)."
