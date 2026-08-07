import argparse
import csv
import http.server
import json
from sparkhub_logger import logger
import os
import re
import socket
import socketserver
import sqlite3
import subprocess
import sys
pyw = sys.executable.replace('python.exe', 'pythonw.exe')
import uuid
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from dotenv import load_dotenv

from sparkhub_paths import PROJECT_ROOT, get_default_port, get_path
load_dotenv(get_path(".env"), override=True)
import router_ai
import ctypes
import sparkhub_crypto
from sparkhub_mcp_orchestrator import orchestrator

# =========================================================
# CONFIGURAÇÕES DO SPARKHUB v2.4.0 UNIVERSAL (SHELL EXECUTE + AUTO-DISCOVERY)
# =========================================================
DEFAULT_PORT = get_default_port(8000)
PORT = DEFAULT_PORT
API_TOKEN = os.getenv("SPARKHUB_API_TOKEN", "").strip()
BASE_DIR = PROJECT_ROOT
STATE_FILE = get_path("state.json")
DB_FILE = get_path("mempalace.db")
MAPA_CSV = get_path("mapa_executaveis.csv")

def init_state():
    if not STATE_FILE.exists():
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "active_project": "",
                    "active_app": "",
                    "total_requests": 0,
                    "last_action": "",
                },
                f,
                indent=2,
            )

init_state()


def find_available_port(start_port: int, max_tries: int = 20) -> int:
    for candidate in [start_port] + list(range(start_port + 1, start_port + max_tries)):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("0.0.0.0", candidate))
                return candidate
            except OSError:
                continue
    raise OSError(f"Não foi possível encontrar uma porta livre a partir de {start_port}")


PORT = find_available_port(PORT)


def update_state(action, project_name="", app_name="", increment=True):
    try:
        data = {"active_project": "", "active_app": "", "total_requests": 0, "last_action": ""}
        if STATE_FILE.exists():
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        
        if increment:
            data["total_requests"] += 1
        data["last_action"] = action
        if project_name:
            data["active_project"] = str(project_name)
        if app_name:
            data["active_app"] = str(app_name)
            
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Erro ao atualizar estado: {e}")

# =========================================================
# MÓDULO AUTO-DISCOVERY DE EXECUTÁVEIS E ATALHOS NO WINDOWS
# =========================================================
def auto_update_mapa_csv():
    """Varre os diretorios padrao de atalhos e executaveis do Windows e gera o mapa_executaveis.csv"""
    scan_dirs = [
        Path(os.environ.get("ProgramData", "C:/ProgramData")) / "Microsoft/Windows/Start Menu/Programs",
        Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
        Path("C:/Users/Public/Desktop"),
        Path(os.path.expanduser("~/Desktop")),
        Path("C:/Program Files"),
        Path("C:/Program Files (x86)"),
        Path("D:/Program Files"),
        Path("D:/Projetos")
    ]

    apps_map = {}

    for base_dir in scan_dirs:
        if not base_dir.exists():
            continue
        try:
            for root, _, files in os.walk(base_dir):
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in [".lnk", ".exe", ".bat", ".cmd", ".url"]:
                        full_path = os.path.join(root, file)
                        clean_name = os.path.splitext(file)[0].lower()
                        if any(un in clean_name for un in ["uninstall", "unins000", "update", "helper", "setup"]):
                            continue
                        if clean_name not in apps_map:
                            apps_map[clean_name] = {
                                "nome": os.path.splitext(file)[0],
                                "caminho": full_path,
                                "tipo": ext.replace(".", "").upper()
                            }
        except Exception as e:
            logger.error(f"Erro ao varrer diretório {base_dir}: {e}")

    try:
        with open(MAPA_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Nome", "Caminho", "Tipo"])
            for app in apps_map.values():
                writer.writerow([app["nome"], app["caminho"], app["tipo"]])
        logger.info(f"[AUTO-DISCOVERY] Mapeados {len(apps_map)} programas/atalhos em {MAPA_CSV}")
    except Exception as e:
        logger.error(f"Erro ao salvar mapa_executaveis.csv: {e}")

auto_update_mapa_csv()

def find_executable_or_shortcut(app_query):
    """Busca inteligente de atalhos/executaveis por correspondencia de nome"""
    query = str(app_query).strip().lower()
    
    if os.path.exists(app_query):
        return app_query

    if MAPA_CSV.exists():
        best_match = None
        try:
            with open(MAPA_CSV, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    nome = row["Nome"].lower()
                    if query == nome:
                        return row["Caminho"]
                    elif query in nome:
                        if not best_match:
                            best_match = row["Caminho"]
            if best_match:
                return best_match
        except Exception as e:
            logger.error(f"Erro ao ler CSV: {e}")

    auto_update_mapa_csv()

    if MAPA_CSV.exists():
        try:
            with open(MAPA_CSV, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    nome = row["Nome"].lower()
                    if query in nome or nome in query:
                        return row["Caminho"]
        except Exception:
            pass

    return app_query

# =========================================================
# HELPER NATIVO WINDOWS SHELLEXECUTE (os.startfile)
# =========================================================
def launch_gui_app(app_cmd):
    """Utiliza os.startfile() nativo do Windows para disparar duplo clique direto no desktop do usuario"""
    try:
        if isinstance(app_cmd, list):
            target = find_executable_or_shortcut(app_cmd[0])
            extra_args = app_cmd[1:]
            if hasattr(os, "startfile") and not extra_args:
                os.startfile(target)
                return
            full_cmd = f'start "" "{target}" ' + " ".join([f'"{a}"' if " " in str(a) else str(a) for a in extra_args])
        else:
            target = find_executable_or_shortcut(app_cmd)
            if hasattr(os, "startfile"):
                os.startfile(target)
                return
            full_cmd = f'start "" "{target}"'
            
        subprocess.Popen(full_cmd, shell=True)
    except Exception as e:
        logger.info(f"Fallback no launch_gui_app: {e}")
        subprocess.Popen(f'start "" "{app_cmd}"', shell=True)

# =========================================================
# PARSER INTELIGENTE DE COMANDOS EM TEXTO LIVRE PARA PASTAS
# =========================================================
def parse_and_create_folder(text):
    """Detecta comandos de criacao de pastas em texto livre e cria o diretorio no disco D:"""
    if not text:
        return None
    text_str = str(text)
    text_lower = text_str.lower()
    keywords = ["crie a pasta", "criar pasta", "crie o diretorio", "criar diretorio", "mkdir", "crie o projeto", "criar projeto"]
    
    if any(k in text_lower for k in keywords):
        match = re.search(r'([a-zA-Z]:[\\/][^\s"]+)', text_str)
        if match:
            target_path = Path(match.group(1).replace('"', ''))
            target_path.mkdir(parents=True, exist_ok=True)
            try:
                mempalace_save("Projetos", "Diretorios", f"Pasta criada via parser inteligente: {target_path}")
            except Exception:
                pass
            update_state("parse_and_create_folder", project_name=str(target_path), app_name="FileSystem")
            return f"Pasta criada com sucesso via parser inteligente: {target_path}"
    return None

# =========================================================
# GERENCIADOR DA LIXEIRA DO WINDOWS (INSTANTÂNEO)
# =========================================================
def get_recycle_bin_items():
    """Retorna os itens da Lixeira do Windows de forma instantanea"""
    cmd = "(New-Object -ComObject Shell.Application).NameSpace(0xa).Items() | Select-Object Name, Path"
    proc = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True, timeout=10)
    out = proc.stdout.strip() or proc.stderr.strip() or "A Lixeira do Windows esta vazia."
    update_state("list_recycle_bin", app_name="Windows Shell")
    return out

# =========================================================
# BANCO DE DADOS MEMPALACE LITE (SQLITE NATIVO)
# =========================================================
def init_mempalace():
    try:
        import sparkhub_db
        sparkhub_db.init_and_migrate_db(DB_FILE)
    except Exception as e:
        logger.error(f"Erro ao inicializar MemPalace DB: {e}")

init_mempalace()

def mempalace_save(wing, room, content):
    wing = str(wing).strip()
    room = str(room).strip()
    content = str(content).strip()
    import sparkhub_db
    success = sparkhub_db.save_memory(wing, room, content, DB_FILE)
    update_state("mempalace_save", app_name="MemPalace")
    return f"Memória registrada com sucesso no MemPalace [Asa: {wing} | Sala: {room}]"

def mempalace_search(query, wing=None):
    query = str(query).strip()
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if wing:
            cursor.execute(
                "SELECT id, wing, room, content, created_at, is_sensitive FROM memories WHERE wing = ? AND content LIKE ? ORDER BY id DESC LIMIT 20",
                (wing, f"%{query}%")
            )
        else:
            cursor.execute(
                "SELECT id, wing, room, content, created_at, is_sensitive FROM memories WHERE content LIKE ? OR wing LIKE ? OR room LIKE ? ORDER BY id DESC LIMIT 20",
                (f"%{query}%", f"%{query}%", f"%{query}%")
            )
        rows = cursor.fetchall()
    
    if not rows:
        return f"Nenhuma memória encontrada para a busca '{query}'."

    results = []
    for r in rows:
        content = r['content']
        if r['is_sensitive']:
            content = sparkhub_crypto.decrypt_content(content)
        results.append(f"• [ID #{r['id']}] [{r['wing']} -> {r['room']}] ({r['created_at']}): {content}")
    
    update_state("mempalace_search", app_name="MemPalace")
    return "\n".join(results)

def mempalace_list(wing=None, room=None, limit=10):
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if wing and room:
            cursor.execute("SELECT id, wing, room, content, created_at, is_sensitive FROM memories WHERE wing = ? AND room = ? ORDER BY id DESC LIMIT ?", (wing, room, limit))
        elif wing:
            cursor.execute("SELECT id, wing, room, content, created_at, is_sensitive FROM memories WHERE wing = ? ORDER BY id DESC LIMIT ?", (wing, limit))
        else:
            cursor.execute("SELECT id, wing, room, content, created_at, is_sensitive FROM memories ORDER BY id DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()

    if not rows:
        return "Nenhuma memória registrada ainda."

    results = []
    for r in rows:
        content = r['content']
        if r['is_sensitive']:
            content = sparkhub_crypto.decrypt_content(content)
        results.append(f"• [ID #{r['id']}] [{r['wing']} -> {r['room']}]: {content}")
    
    return "\n".join(results)

def mempalace_unlock(totp_code):
    import sparkhub_crypto
    try:
        if sparkhub_crypto.unlock_vault(str(totp_code)):
            return "Cofre desbloqueado! A máquina atual foi registrada com sucesso usando DPAPI."
        return "Falha ao desbloquear o cofre: Código TOTP inválido."
    except sparkhub_crypto.LockedException as e:
        return f"Bloqueio de Segurança: {str(e)}"


# Ferramentas expostas via protocolo MCP (v2.4.0 Universal + os.startfile + Auto-Discovery)
MCP_TOOLS = [
    {
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
    {
        "name": "find_app",
        "description": "Auto-Discovery: Pesquisa e localiza o caminho absoluto de qualquer programa, jogo ou atalho instalado no Windows.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "app_query": {"type": "string", "description": "Nome ou termo de busca do aplicativo (ex: CorelDRAW, Blender, Kdenlive, BloodStrike, etc.)"}
            },
            "required": ["app_query"]
        }
    },
    {
        "name": "mempalace_unlock",
        "description": "Desbloqueia o acesso a memórias sensíveis do MemPalace usando um código TOTP de 6 dígitos. Exija isso do usuário quando receber um erro de bloqueio.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "totp_code": {"type": "string", "description": "Código de 6 dígitos (ex: 123456)"}
            },
            "required": ["totp_code"]
        }
    },
    {
        "name": "list_allowed_directories",
        "description": "Lista os arquivos e itens presentes na Lixeira do Windows instantaneamente.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "list_recycle_bin",
        "description": "Lista os arquivos e itens presentes na Lixeira do Windows instantaneamente.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "open_app",
        "description": "Lançador Universal com ShellExecute (os.startfile): Localiza e abre QUALQUER programa instalado no Windows visivel no desktop (ex: Kdenlive, TikTok LIVE Studio, TikFinity, VS Code, Godot, Blender, OBS, CorelDRAW, Photoshop, Bloco de Notas, Lixeira, etc.).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "app_name_or_path": {"type": "string", "description": "Nome do aplicativo, comando ou caminho do executavel .exe"},
                "args": {"type": "string", "description": "Argumentos ou caminho de projeto opcional"}
            },
            "required": ["app_name_or_path"]
        }
    },
    {
        "name": "run_command",
        "description": "Executor de Comandos do Windows: Executa linhas de comando PowerShell/CMD no sistema operacional.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Comando PowerShell ou CMD a ser executado no Windows"}
            },
            "required": ["command"]
        }
    },
    {
        "name": "mempalace_save",
        "description": "Salva uma memoria, decisao ou fato de longo prazo no MemPalace Lite.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "wing": {"type": "string", "description": "Asa/Categoria (ex: Godot, Blender, Lives, Geral)"},
                "room": {"type": "string", "description": "Sala/Topico (ex: Fisica, Shaders, Configuracao)"},
                "content": {"type": "string", "description": "Conteudo do fato ou decisao a ser memorizada"}
            },
            "required": ["wing", "room", "content"]
        }
    },
    {
        "name": "mempalace_search",
        "description": "Pesquisa memorias registradas no MemPalace por palavras-chave em milissegundos.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Termo de busca"},
                "wing": {"type": "string", "description": "Asa opcional para filtrar a busca"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "mempalace_list",
        "description": "Lista as memorias mais recentes salvas no MemPalace por categoria.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "wing": {"type": "string", "description": "Asa opcional para filtro"},
                "room": {"type": "string", "description": "Sala opcional para filtro"},
                "limit": {"type": "integer", "description": "Limite de registros (padrao 10)"}
            }
        }
    },
    {
        "name": "macro_setup_project",
        "description": "Cria a estrutura de pastas e arquivos de um novo projeto e abre no editor em 1 passo.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "base_dir": {"type": "string", "description": "Caminho da pasta do projeto (ex: D:/Projetos/MeuJogo)"},
                "folders": {"type": "array", "items": {"type": "string"}, "description": "Lista de subpastas a criar"},
                "files": {"type": "object", "description": "Dicionario de arquivos e conteudos"}
            },
            "required": ["base_dir"]
        }
    },
    {
        "name": "open_vscode",
        "description": "Atalhos de edicao: Abre o VS Code no caminho especificado.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Caminho do arquivo ou diretorio"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "open_godot",
        "description": "Atalhos de jogos: Inicia a engine Godot no projeto indicado.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Caminho do projeto Godot"}
            }
        }
    },
    {
        "name": "run_blender_script",
        "description": "Atalhos 3D: Executa um script Python dentro do Blender 3D.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "script_path": {"type": "string", "description": "Caminho do arquivo Python .py"},
                "file_path": {"type": "string", "description": "Caminho do arquivo .blend (opcional)"}
            }
        }
    },
    {
        "name": "open_kdenlive",
        "description": "Atalhos de video: Inicia o Kdenlive em um projeto ou pasta.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Caminho opcional do projeto ou pasta"}
            }
        }
    },
    {
        "name": "open_tiktok_live",
        "description": "Atalhos de live: Inicia o TikTok LIVE Studio no Windows.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Caminho opcional"}
            }
        }
    },
    {
        "name": "open_tikfinity",
        "description": "Atalhos de live: Inicia o aplicativo/painel TikFinity.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Caminho ou URL opcional"}
            }
        }
    },
    {
        "name": "create_structure",
        "description": "Cria estrutura personalizada de diretorios e arquivos no disco local.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "base_dir": {"type": "string", "description": "Diretorio base"},
                "folders": {"type": "array", "items": {"type": "string"}},
                "files": {"type": "object"}
            },
            "required": ["base_dir"]
        }
    },
    {
        "name": "search_gmail",
        "description": "Busca e-mails recentes na caixa de entrada do Gmail usando queries.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Termo de busca (ex: 'esposa', 'voo', 'from:chefe@email.com')"},
                "max_results": {"type": "integer", "description": "Numero maximo de resultados (default: 5)"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "search_drive",
        "description": "Busca arquivos no Google Drive (PDFs, Docs, etc) contendo texto especifico.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Termo de busca contido no arquivo"},
                "max_results": {"type": "integer", "description": "Numero maximo de resultados (default: 3)"}
            },
            "required": ["query"]
        }
    }
]



# =========================================================
# CONSULTA PROATIVA AO MEMPALACE
# =========================================================

# =========================================================
# ROTEADOR MULTI-MODE (SPARKHUB AI ROUTER)
# =========================================================
# detect_heavy_load delegated to router_ai.detect_heavy_load
from router_ai import detect_heavy_load as _detect_heavy_load

def detect_heavy_load():
    return _detect_heavy_load()

# call_llm_api delegated to router_ai.call_llm_api
from router_ai import call_llm_api as _call_llm_api

def call_llm_api(url, payload, headers):
    return _call_llm_api(url, payload, headers)

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

    # =========================================================
    # TRÍPLICE CASCATA ANTIFRÁGIL DE TOKENS (CUSTO R$ 0,00)
    # =========================================================

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
            logger.error(f"[ROTEADOR WARN] Camada 1 falhou ({e}). Acionando Camada 2...")

    # 2. CAMADA 2: OpenRouter Free (openrouter/free)
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    if openrouter_key and openrouter_key != "sua_chave_openrouter_aqui":
        headers = {"Authorization": f"Bearer {openrouter_key}", "Content-Type": "application/json"}
        payload_openai["model"] = "openrouter/free"
        res = call_llm_api("https://openrouter.ai/api/v1/chat/completions", payload_openai, headers)
        if not res.startswith("[ERRO API]"):
            return f"🤖 [Antigravity | Cloud OpenRouter]:\n{res}"
        logger.error(f"[ROTEADOR WARN] Camada 2 falhou ({res}). Acionando Camada 3...")

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
            logger.error(f"[ROTEADOR WARN] Camada 3 também falhou: {e}")

    return "[❌ AUDITORIA CRÍTICA] Colapso Total da Tríplice Cascata. Nenhum LLM disponível (Local, OpenRouter, Gemini)."

# Override local router with external implementation (router_ai.py)
route_ai_request = router_ai.route_ai_request

def load_env_phone():
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("WHATSAPP_PHONE_NUMBER="):
                    return line.split("=", 1)[1].strip()
    return "Desconhecido"

def load_workspace_secret():
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("WORKSPACE_TOOL_SECRET="):
                    return line.split("=", 1)[1].strip()
    return ""

def proactive_memory_check(tool_name, args):
    if tool_name not in ["create_structure", "macro_setup_project", "run_command", "ask_ai"]:
        return ""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT wing, room, content FROM memories WHERE wing IN ('Profile', 'System', 'Projects', 'Skills', 'Projetos', 'Geral', 'Cloud', 'Email', 'Documento') ORDER BY id DESC LIMIT 8")
            rows = cursor.fetchall()
            
        memories = ""
        if rows:
            memories = "\n".join([f"• [{r['wing']} -> {r['room']}]: {r['content']}" for r in rows])
            
        if tool_name == "ask_ai":
            phone = load_env_phone()
            identity = f"Você é o SparkHub AI, o Orquestrador Pessoal. Seu mestre é Alexandre Cavalcante Curvelo (Ale / Curvelo), morador de Embu-Guaçu/SP. Telefone do mestre: {phone}.\nUse as memórias abaixo (se houver) para embasar sua resposta. Seja direto e objetivo, sem floreios.\n\n"
            return f"[💡 Contexto Proativo do Sistema]:\n{identity}{memories}"
            
        if not rows:
            return ""
        return f"\n\n[💡 Contexto Proativo do MemPalace]:\n{memories}"
    except Exception:
        return ""

def execute_tool(name, args):
    """Executa as acoes nativas no Windows e MemPalace v3.0 com os.startfile(), Auto-Discovery, Auditoria e Contexto Proativo"""
    
    # 1. Recuperar contexto proativo
    proactive_context = proactive_memory_check(name, args)
    
    # Função auxiliar para injetar contexto (apenas para ferramentas visuais, ask_ai faz diferente)
    def finalize(msg):
        if name == "ask_ai": return msg
        return msg + proactive_context

    if name == "ask_ai":
        prompt = args.get("prompt", "")
        profile = args.get("profile", "auto")
        update_state("ask_ai", app_name=profile, increment=False)
        
        prompt_lower = prompt.lower().strip()
        
        try:
            # 1. Tipo 2: SyncRequisições Antifrágil (Delegação para o Script Mestre)
            if any(word in prompt_lower for word in ['sync', 'sincroniz', 'status', 'requisi']):
                logger.info(f"[ORQUESTRADOR] Rota 2 (Status/Sync) ativada.")
                try:
                    # Executa o script mestre diretamente e retorna apenas as últimas linhas limpas
                    out = subprocess.check_output([sys.executable, str(get_path("sync_requisicoes_master.py")), "--scope=sheets"], stderr=subprocess.STDOUT, text=True)
                    return f"🤖 [Relatório do Sistema Local]:\n{out.strip()}"
                except subprocess.CalledProcessError as e:
                    return f"⚠️ [Erro na Sincronização]: {e.output}"
                    
            # 2. Tipo 1: Identidade (Leitura Direta Segura)
            elif any(word in prompt_lower for word in ['quem sou eu', 'meu telefone', 'onde eu moro', 'quem e voce']):
                logger.info(f"[ORQUESTRADOR] Rota 1 (Identidade) ativada.")
                clean_identity = proactive_context.replace("[💡 Contexto Proativo do Sistema]:\n", "")
                return f"🤖 [Perfil Local Carregado]:\n{clean_identity}"
                
            # 3. Tipo 3: Nuvem do Google Workspace (Drive / Gmail)
            elif any(word in prompt_lower for word in ['drive', 'documento', 'gdd', 'email', 'e-mail', 'gmail']):
                logger.info(f"[ORQUESTRADOR] Rota 3 (Workspace) ativada.")
                import workspace_agent
                workspace_context = ""
                
                # Se for email
                if any(word in prompt_lower for word in ['email', 'e-mail', 'gmail']):
                    # Tenta extrair a intenção da query, ou busca os mais recentes
                    termo = prompt_lower.replace('procure', '').replace('no email', '').replace('e-mail', '').strip()
                    if not termo or termo in ['email', 'gmail']: termo = "is:unread" # fallback
                    res = workspace_agent.search_gmail(termo)
                    workspace_context += f"\\n[Resultado Gmail]: {res}"
                
                # Se for drive/documento
                if any(word in prompt_lower for word in ['drive', 'documento', 'gdd']):
                    termo = prompt_lower.replace('procure', '').replace('no drive', '').replace('documento', '').strip()
                    if not termo or termo == 'drive': termo = "SparkHub"
                    res = workspace_agent.search_drive_docs(termo)
                    workspace_context += f"\\n[Resultado Drive]: {res}"
                
                logger.info(f"[ORQUESTRADOR] Injetando dados do Workspace na Rota 5...")
                if proactive_context:
                    prompt = f"{proactive_context}\\n{workspace_context}\\n\\n[PERGUNTA DO USUÁRIO]:\\n{prompt}"
                else:
                    prompt = f"[💡 Contexto do Google Workspace]:\\n{workspace_context}\\n\\n[PERGUNTA DO USUÁRIO]:\\n{prompt}"
                return route_ai_request(prompt, profile)

            # 4. Tipo 4: Comandos do SO
            elif prompt_lower.startswith('abre ') or prompt_lower.startswith('abrir '):
                alvo = prompt_lower.replace('abre ', '').replace('abrir ', '').strip()
                logger.info(f"[ORQUESTRADOR] Rota 4 (Ação SO) ativada para '{alvo}'.")
                return execute_tool("open_app", {"app_name_or_path": alvo})
                
            # 4. Tipo 5: LLM (Gemini / Ollama) com injeção de contexto
            else:
                logger.info(f"[ORQUESTRADOR] Rota 5 (Raciocínio) ativada.")
                # O AI Roteador ingere o contexto proativo COMO PARTE DO PROMPT para a nuvem processar!
                if proactive_context:
                    prompt = f"{proactive_context}\n\n[PERGUNTA DO USUÁRIO]:\n{prompt}"
                return route_ai_request(prompt, profile)
                
        except Exception as e:
            return f"[⚡ CIRCUIT BREAKER (Orquestrador)]: Ocorreu uma falha imprevista na rota. Detalhe: {str(e)}"

    if name == "find_app":
        query = args.get("app_query", "")
        res_path = find_executable_or_shortcut(query)
        update_state("find_app", app_name=query, increment=False)
        return finalize(f"Auto-Discovery encontrou para '{query}': {res_path}")

    if name == "list_recycle_bin":
        return finalize(get_recycle_bin_items())

    app_target = args.get("app_name_or_path", "") or args.get("command", "") or name
    if "lixeira" in str(app_target).lower() or "recycle.bin" in str(app_target).lower():
        return finalize(get_recycle_bin_items())

    folder_res = parse_and_create_folder(app_target)
    if folder_res:
        return finalize(folder_res)

    if name == "open_app":
        extra_args = args.get("args", "")
        parsed = parse_and_create_folder(f"{app_target} {extra_args}")
        if parsed: return finalize(parsed)
            
        resolved_app = find_executable_or_shortcut(app_target)
        if not os.path.exists(resolved_app) and not resolved_app.startswith("http"):
            return finalize(f"[❌ AUDITORIA FALHA] O executável/atalho não foi encontrado no disco: {resolved_app}")
            
        cmd = [resolved_app]
        if extra_args: cmd.append(str(extra_args))
        launch_gui_app(cmd)
        update_state("open_app", project_name=str(extra_args), app_name=resolved_app, increment=False)
        return finalize(f"[✅ AUDITORIA SUCESSO] Programa '{app_target}' (ShellExecute: {resolved_app}) aceito pelo Windows e iniciado visível.")

    elif name == "run_command":
        cmd_str = args.get("command", "")
        if "lixeira" in cmd_str.lower() or "recycle" in cmd_str.lower():
            return finalize(get_recycle_bin_items())
            
        parsed = parse_and_create_folder(cmd_str)
        if parsed: return finalize(parsed)

        proc = subprocess.run(["powershell", "-Command", cmd_str], capture_output=True, text=True, timeout=30)
        out = proc.stdout.strip() or proc.stderr.strip() or "Comando executado com sucesso."
        update_state("run_command", app_name="PowerShell", increment=False)
        return finalize(f"[✅ AUDITORIA (Exit Code: {proc.returncode})]:\\n{out}")

    elif name == "mempalace_save":
        return finalize(mempalace_save(args.get("wing", "Geral"), args.get("room", "Geral"), args.get("content", "")))

    elif name == "mempalace_search":
        return finalize(mempalace_search(args.get("query", ""), wing=args.get("wing")))

    elif name == "mempalace_list":
        return finalize(mempalace_list(wing=args.get("wing"), room=args.get("room"), limit=args.get("limit", 10)))

    elif name == "mempalace_unlock":
        return finalize(mempalace_unlock(args.get("totp_code", "")))

    elif name == "open_kdenlive":
        path = args.get("path", "")
        target = find_executable_or_shortcut("kdenlive")
        kdenlive_cmd = [target, path] if path else [target]
        launch_gui_app(kdenlive_cmd)
        update_state("open_kdenlive", project_name=path, app_name="Kdenlive", increment=False)
        return finalize(f"[✅ AUDITORIA] Kdenlive iniciado visível{' em: ' + path if path else ''}.")

    elif name == "open_tiktok_live":
        path = args.get("path", "")
        target = find_executable_or_shortcut("TikTok LIVE Studio")
        cmd = [path] if path else [target]
        launch_gui_app(cmd)
        update_state("open_tiktok_live", app_name="TikTok LIVE Studio", increment=False)
        return finalize("[✅ AUDITORIA] TikTok LIVE Studio iniciado visível.")

    elif name == "open_tikfinity":
        path = args.get("path", "")
        cmd = [path] if path else ["https://tikfinity.zerody.one/"]
        launch_gui_app(cmd)
        update_state("open_tikfinity", app_name="TikFinity", increment=False)
        return finalize("[✅ AUDITORIA] TikFinity iniciado visível.")

    elif name == "open_vscode":
        path = args.get("path", ".")
        target = find_executable_or_shortcut("code")
        launch_gui_app([target, path])
        update_state("open_vscode", project_name=path, app_name="VS Code", increment=False)
        return finalize(f"[✅ AUDITORIA] VS Code aberto visível em: {path}")

    elif name == "open_godot":
        path = args.get("path", "")
        target = find_executable_or_shortcut("godot")
        godot_cmd = [target, "--path", path] if path else [target]
        launch_gui_app(godot_cmd)
        update_state("open_godot", project_name=path, app_name="Godot", increment=False)
        return finalize(f"[✅ AUDITORIA] Godot iniciado visível em: {path}")

    elif name == "run_blender_script":
        script_path = args.get("script_path", "")
        file_path = args.get("file_path", "")
        target = find_executable_or_shortcut("blender")
        cmd = [target]
        if file_path: cmd.append(file_path)
        if script_path: cmd.extend(["-P", script_path])
        launch_gui_app(cmd)
        update_state("run_blender_script", project_name=script_path, app_name="Blender", increment=False)
        return finalize("[✅ AUDITORIA] Comando do Blender executado visível.")
        
    elif name == "sync_requisicoes":
        update_state("sync_requisicoes", increment=False)
        script_path = get_path("sync_requisicoes_master.py")
        res = subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True)
        out = res.stdout + ("\n" + res.stderr if res.stderr else "")
        return finalize(f"[✅ SYNC EXECUTADO]\n{out}")

    elif name == "create_structure":
        base_dir = Path(args.get("base_dir", "."))
        folders = args.get("folders", [])
        files = args.get("files", {})

        total_items = len(folders) + len(files)
        created_count = 0
        failed_items = []

        for folder in folders:
            folder_path = base_dir / folder
            try:
                folder_path.mkdir(parents=True, exist_ok=True)
                if folder_path.exists(): created_count += 1
                else: failed_items.append(f"Pasta: {folder}")
            except Exception as e:
                failed_items.append(f"Pasta: {folder} ({e})")

        for file_rel_path, content in files.items():
            file_full_path = base_dir / file_rel_path
            try:
                file_full_path.parent.mkdir(parents=True, exist_ok=True)
                with open(file_full_path, "w", encoding="utf-8") as f:
                    f.write(content)
                if file_full_path.exists(): created_count += 1
                else: failed_items.append(f"Arquivo: {file_rel_path}")
            except Exception as e:
                failed_items.append(f"Arquivo: {file_rel_path} ({e})")

        update_state("create_structure", project_name=str(base_dir))
        
        audit_msg = f"[✅ AUDITORIA SINTÉTICA] {created_count}/{total_items} itens criados com sucesso em {base_dir}"
        if failed_items:
            audit_msg += "\\nFalhas:\\n- " + "\\n- ".join(failed_items)
            
        return finalize(f"Estrutura processada.\\n{audit_msg}")

    elif name == "macro_setup_project":
        base_dir = Path(args.get("base_dir", "D:/Projetos/NovoProjeto"))
        folders = args.get("folders", ["scripts", "scenes", "assets"])
        files = args.get("files", {"README.md": "# Projeto Criado via Spark\\n"})

        total_items = len(folders) + len(files)
        created_count = 0
        failed_items = []

        for folder in folders:
            folder_path = base_dir / folder
            try:
                folder_path.mkdir(parents=True, exist_ok=True)
                if folder_path.exists(): created_count += 1
                else: failed_items.append(f"Pasta: {folder}")
            except Exception as e:
                failed_items.append(f"Pasta: {folder} ({e})")

        for file_rel_path, content in files.items():
            file_full_path = base_dir / file_rel_path
            try:
                file_full_path.parent.mkdir(parents=True, exist_ok=True)
                with open(file_full_path, "w", encoding="utf-8") as f:
                    f.write(content)
                if file_full_path.exists(): created_count += 1
                else: failed_items.append(f"Arquivo: {file_rel_path}")
            except Exception as e:
                failed_items.append(f"Arquivo: {file_rel_path} ({e})")

        target = find_executable_or_shortcut("code")
        launch_gui_app([target, str(base_dir)])
        update_state("macro_setup_project", project_name=str(base_dir), app_name="VS Code")
        
        audit_msg = f"[✅ AUDITORIA SINTÉTICA] {created_count}/{total_items} itens criados com sucesso. VS Code aberto em {base_dir}"
        if failed_items:
            audit_msg += "\\nFalhas:\\n- " + "\\n- ".join(failed_items)
            
        return finalize(f"Macro Setup Concluído.\\n{audit_msg}")

    elif name in ["search_gmail", "search_drive"]:
        # Fase 5: Trava de Segurança Mínima
        secret_token = load_workspace_secret()
        if not secret_token:
            return finalize("[❌ SEGURANÇA] Acesso negado. A variável WORKSPACE_TOOL_SECRET não foi configurada no .env.")
        
        try:
            import google_workspace_tools
            if name == "search_gmail":
                return finalize(google_workspace_tools.search_gmail(args.get("query", ""), args.get("max_results", 5)))
            else:
                return finalize(google_workspace_tools.search_drive(args.get("query", ""), args.get("max_results", 3)))
        except Exception as e:
            return finalize(f"[ERRO WORKSPACE] {e}")

    else:
        parsed = parse_and_create_folder(name)
        if parsed:
            return finalize(parsed)
        raise ValueError(f"Ferramenta desconhecida: {name}")

class SparkHubTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


class LocalHubMCPHandler(http.server.BaseHTTPRequestHandler):

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, HEAD, OPTIONS")

    def _send_json(self, status_code, data):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def _send_auth_error(self):
        self._send_json(401, {"jsonrpc": "2.0", "error": {"code": -32001, "message": "Unauthorized"}})

    def _is_authenticated(self):
        query = parse_qs(urlparse(self.path).query)
        token_from_query = query.get("token", [""])[0]
        auth_header = self.headers.get("Authorization", "")
        token_from_header = ""
        if auth_header.startswith("Bearer "):
            token_from_header = auth_header[7:].strip()
        elif auth_header:
            token_from_header = auth_header.strip()

        provided_token = token_from_header or token_from_query
        return API_TOKEN != "" and provided_token == API_TOKEN

    def do_HEAD(self):
        if not self._is_authenticated():
            self._send_auth_error()
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._send_cors_headers()
        self.end_headers()

    def do_OPTIONS(self):
        if not self._is_authenticated():
            self._send_auth_error()
            return
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        if not self._is_authenticated():
            self._send_auth_error()
            return
        if self.path.startswith("/sse") or self.path.startswith("/mcp"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self._send_cors_headers()
            self.end_headers()

            msg = "event: endpoint\ndata: /messages\n\n"
            self.wfile.write(msg.encode("utf-8"))
            self.wfile.flush()
            return

        state_data = {}
        if STATE_FILE.exists():
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                state_data = json.load(f)

        self._send_json(200, {
            "jsonrpc": "2.0",
            "name": "SparkHub MCP Server Universal",
            "version": "2.5.0",
            "status": "online",
            "mcp_version": "2024-11-05",
            "tools": [t["name"] for t in MCP_TOOLS],
            "state": state_data
        })

    def do_POST(self):
        if not self._is_authenticated():
            self._send_auth_error()
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_length)

        try:
            payload = json.loads(body_bytes.decode("utf-8"))
        except Exception:
            self._send_json(400, {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error: JSON invalido"}})
            return

        # 1. Requisicoes MCP JSON-RPC 2.0
        if isinstance(payload, dict) and "jsonrpc" in payload:
            req_id = payload.get("id")
            method = payload.get("method")
            params = payload.get("params", {})

            logger.info(f"[MCP METHOD] {method} (id={req_id})")

            if method == "initialize":
                self._send_json(200, {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": {
                            "name": "SparkHub MCP Server Universal",
                            "version": "2.5.0"
                        }
                    }
                })

            elif method == "notifications/initialized" or method == "ping":
                self._send_json(200, {"jsonrpc": "2.0", "id": req_id, "result": {}})

            elif method == "tools/list":
                self._send_json(200, {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "tools": MCP_TOOLS
                    }
                })

            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                try:
                    update_state(tool_name, increment=True)
                    # Delegação para o Orchestrator (Deduplicação, Auto-healing, Circuit Breaker, Telemetria)
                    from sparkhub_mcp_orchestrator import MCPRequest
                    from datetime import datetime
                    
                    req_obj = MCPRequest(
                        request_id=str(req_id) if req_id else str(uuid.uuid4()),
                        origin=self.headers.get("User-Agent", "unknown"),
                        tool=tool_name,
                        payload=params,
                        timestamp=datetime.now(),
                        ttl_seconds=30
                    )
                    
                    orchestrator_resp = orchestrator.process(req_obj, execute_tool)
                    
                    # O orchestrator_resp já traz a formatação {"result": ...} ou {"error": ...}
                    resp_dict = {
                        "jsonrpc": "2.0",
                        "id": req_id
                    }
                    resp_dict.update(orchestrator_resp)
                    
                    self._send_json(200 if "result" in orchestrator_resp else 503, resp_dict)

                except Exception as e:
                    self._send_json(200, {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {
                            "code": -32603,
                            "message": f"Erro ao executar ferramenta {tool_name}: {str(e)}"
                        }
                    })

            else:
                self._send_json(200, {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Metodo {method} nao encontrado."}
                })
            return

        # 2. Formato Legado Spark (Action + Params) ou Texto Livre
        action = payload.get("action")
        params = payload.get("params", {})

        if action:
            parsed = parse_and_create_folder(action)
            if parsed:
                self._send_json(200, {"status": "sucesso", "mensagem": parsed})
                return

            try:
                update_state(action, increment=True)
                res_msg = execute_tool(action, params)
                self._send_json(200, {"status": "sucesso", "mensagem": res_msg})
            except Exception as e:
                self._send_json(500, {"status": "erro", "mensagem": str(e)})
        else:
            self._send_json(400, {"status": "erro", "mensagem": "Formato de payload nao reconhecido."})


if __name__ == "__main__":
    # Previne múltiplas instâncias da API Principal
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "SparkHubAPIMutex_v3")
    if ctypes.windll.kernel32.GetLastError() == 183: # ERROR_ALREADY_EXISTS
        logger.info("[API] Uma instância já está rodando. Encerrando.")
        sys.exit(0)
        
    parser = argparse.ArgumentParser(description="SparkHub v3.0 - CLI e Servidor MCP")
    parser.add_argument("tool", nargs="?", help="Nome da ferramenta para executar via CLI (ex: open_app, run_command)")
    parser.add_argument("args", nargs="*", help="Argumentos da ferramenta em formato chave=valor ou string direta")
    parser.add_argument("--profile", default="auto", help="Perfil do Multi-Mode para ask_ai (auto, cloud, vram_fast, etc)")
    
    cli_args = parser.parse_args()
    
    if cli_args.tool:
        # Modo CLI
        logger.info(f"=== SPARKHUB v3.0 MODO CLI ===")
        tool_name = cli_args.tool
        # Parse simple arguments
        tool_kwargs = {}
        if len(cli_args.args) == 1 and "=" not in cli_args.args[0]:
            # Guess mapping based on tool
            if tool_name == "run_command": tool_kwargs["command"] = cli_args.args[0]
            elif tool_name == "open_app": tool_kwargs["app_name_or_path"] = cli_args.args[0]
            elif tool_name == "find_app": tool_kwargs["app_name"] = cli_args.args[0]
            elif tool_name == "mempalace_search": tool_kwargs["query"] = cli_args.args[0]
            elif tool_name == "ask_ai": tool_kwargs["prompt"] = cli_args.args[0]
            else: tool_kwargs["path"] = cli_args.args[0]
        else:
            for arg in cli_args.args:
                if "=" in arg:
                    k, v = arg.split("=", 1)
                    tool_kwargs[k] = v
        if cli_args.profile and tool_name == "ask_ai":
            tool_kwargs["profile"] = cli_args.profile
        
        logger.info(f"Executando ferramenta: {tool_name} com args: {tool_kwargs}\\n")
        try:
            result = execute_tool(tool_name, tool_kwargs)
            logger.info("=== RESULTADO ===")
            logger.info(result)
        except Exception as e:
            logger.error(f"[ERRO] {e}")
    else:
        # Modo Servidor MCP Original
        logger.info(f"=== SERVIDOR SPARKHUB v3.0 (SHELLEXECUTE / AUTO-DISCOVERY / CLI) RODANDO NA PORTA {PORT} ===")
        logger.info("Execucao nativa na sessao interativa com os.startfile() e auditoria pos-acao.")
        import subprocess
        pyw = sys.executable.replace('python.exe', 'pythonw.exe')
        try:
            
            subprocess.Popen([pyw, os.path.join(os.path.dirname(os.path.abspath(__file__)), "sparkhub_dashboard.py")], creationflags=subprocess.CREATE_NO_WINDOW)
            
            # Dispara mudança visual do atalho
            import socket
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    sock.sendto(b"icon_core", ("127.0.0.1", 8087))
            except: pass
        except Exception as e:
            logger.warning(f"[WARN] Nao foi possivel iniciar widgets/UI: {e}")
            
        with SparkHubTCPServer(("", PORT), LocalHubMCPHandler) as httpd:
            logger.info(f"=== SERVIDOR SPARKHUB v3.0 RODANDO EM http://127.0.0.1:{PORT}/ ===")
            httpd.serve_forever()

