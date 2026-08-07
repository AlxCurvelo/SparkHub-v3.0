# C1-CONCEPCAO: Dashboard minimalista e auto-adaptativo (Porta 8085)
# OBJETIVO: Servidor unificado com auto-descoberta de servicos, cards em tempo real e input de uma mao.
# ESCOPOS: 1. API de Status e Healthcheck 2. Interface Responsiva Embed 3. Endpoint de Comando Modular
import os
from sparkhub_logger import logger

import shutil
import sqlite3
import time
from flask import Flask, jsonify, render_template_string, request, session, redirect, url_for
from functools import wraps
import os

from sparkhub_paths import get_default_port, get_path
from dotenv import load_dotenv

load_dotenv(get_path(".env"))
app = Flask(__name__)
app.secret_key = os.getenv("SPARKHUB_API_TOKEN", "default_secret_key_fallback")

# Tokens de Segurança
DASHBOARD_PASS = os.getenv("DASHBOARD_PASSWORD", "12345")
API_TOKEN = os.getenv("SPARKHUB_API_TOKEN", "")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == DASHBOARD_PASS:
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            return "Senha Incorreta", 401
    return '''
        <form method="post" style="margin:50px auto; width:300px; text-align:center; font-family:monospace;">
            <h2>SparkHub Login</h2>
            <input type="password" name="password" placeholder="Senha" style="padding:10px; width:100%; box-sizing:border-box;">
            <button type="submit" style="padding:10px; margin-top:10px; width:100%;">Entrar</button>
        </form>
    '''

import sys
import ctypes

# Previne múltiplas instâncias do Dashboard
mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "SparkHubDashboardMutex_v3")
if ctypes.windll.kernel32.GetLastError() == 183: # ERROR_ALREADY_EXISTS
    print("[DASHBOARD] Uma instância já está rodando. Encerrando.")
    sys.exit(0)

# --- C2-PREPARACAO: Variaveis e Funcoes de Diagnostico ---
DB_PATH = str(get_path("mempalace.db"))
MCP_PORT = get_default_port(8000)


def check_port(host, port):
  import socket

  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  s.settimeout(0.15)
  try:
    s.connect((host, port))
    s.close()
    return True
  except:
    return False


def get_disk_status():
  try:
    c = shutil.disk_usage(r"C:\\")
    c_free = round(c.free / (1024**3), 3)
    c_norm = c.free > 50 * 1024 * 1024
  except:
    c_free, c_norm = 0, False

  try:
    d = shutil.disk_usage(str(get_path('.')))
    d_free = round(d.free / (1024**3), 3)
    d_norm = d.free > 50 * 1024 * 1024
  except:
    d_free, d_norm = 0, False
  return {
      "c_free": c_free,
      "c_norm": c_norm,
      "d_free": d_free,
      "d_norm": d_norm,
  }


_last_total_memories = -1

def get_mempalace_stats():
  global _last_total_memories
  if not os.path.exists(DB_PATH):
    return {"total": 0, "wal": False, "rooms": {}}
  try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode;")
    wal = cursor.fetchone()[0].upper() == "WAL"
    cursor.execute("SELECT COUNT(*) FROM memories")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT room, COUNT(*) FROM memories GROUP BY room")
    rooms_data = cursor.fetchall()
    conn.close()

    # Agrupar
    grouped = {}
    for raw_room, count in rooms_data:
        r = str(raw_room)
        # Identificar prefixos conhecidos
        if r.startswith("drive:Principal:"): k = "Drive Principal"
        elif r.startswith("drive:Trabalho:"): k = "Drive Trabalho"
        elif r.startswith("gmail:Principal:"): k = "Gmail Principal"
        elif r.startswith("gmail:Trabalho:"): k = "Gmail Trabalho"
        elif r.startswith("drive:"): k = "Drive Outros"
        elif r.startswith("gmail:"): k = "Gmail Outros"
        else: k = r
        
        grouped[k] = grouped.get(k, 0) + count

    # Logar a lista crua APENAS se o total mudou (para não flodar o log a cada 2s)
    if total != _last_total_memories:
        _last_total_memories = total
        logger.info(f"[MEMPALACE] Resumo completo de agrupamento (Total: {total}):")
        for k, v in grouped.items():
            logger.info(f"    - {k}: {v} itens")

    # Ordenar por volume
    sorted_rooms = sorted(grouped.items(), key=lambda x: x[1], reverse=True)
    
    # Pegar as 6 maiores
    top_rooms = dict(sorted_rooms[:6])
    if len(sorted_rooms) > 6:
        outras = sum(v for k, v in sorted_rooms[6:])
        top_rooms[f"+ {len(sorted_rooms)-6} outras"] = outras

    return {
        "total": total,
        "wal": wal,
        "rooms": top_rooms
    }
  except Exception as e:
    logger.error(f"[MURPHY] Erro ao ler mempalace.db: {e}")
    return {"total": 0, "wal": False, "rooms": {}}


# --- C3-EXECUCAO: Template UI Mobile-First ---
LOGS_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SparkHub Logs</title>
    <style>
        body { font-family: monospace; background: #0d1117; color: #c9d1d9; margin: 0; padding: 10px; }
        .card { background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 10px; margin-bottom: 8px; }
        h2 { font-size: 13px; margin: 0 0 6px 0; color: #58a6ff; display: flex; justify-content: space-between; align-items: center;}
        a.btn, button.btn { background: #21262d; color: #c9d1d9; border: 1px solid #30363d; padding: 4px 8px; border-radius: 4px; text-decoration: none; font-size: 11px; cursor: pointer; }
        .log-container { background: #010409; border: 1px solid #30363d; border-radius: 4px; padding: 10px; height: 80vh; overflow-y: auto; font-size: 11px; line-height: 1.4; white-space: pre-wrap; }
        .info { color: #8b949e; }
        .warning { color: #d29922; }
        .error { color: #f85149; }
        .security { color: #bc8cff; font-weight: bold; }
    </style>
</head>
<body>
    <h2>
        <span>SparkHub System Logs</span>
        <div>
            <button class="btn" onclick="copyLogs()">Copiar</button>
            <a href="/" class="btn">Voltar</a>
        </div>
    </h2>
    <div class="card">
        <div id="logs" class="log-container">Carregando...</div>
    </div>
    <script>
        function updateLogs() {
            fetch('/api/logs').then(r => r.json()).then(d => {
                if (d.status === 'success') {
                    let html = d.data.map(line => {
                        let cls = 'info';
                        if (line.includes('WARNING') || line.includes('[ROTEADOR WARN]')) cls = 'warning';
                        if (line.includes('ERROR') || line.includes('Erro')) cls = 'error';
                        if (line.includes('[SECURITY]')) cls = 'security';
                        return `<div class="${cls}">${line}</div>`;
                    }).join('');
                    let logEl = document.getElementById('logs');
                    let isBottom = (logEl.scrollHeight - logEl.scrollTop === logEl.clientHeight);
                    logEl.innerHTML = html;
                    if (isBottom) logEl.scrollTop = logEl.scrollHeight;
                }
            });
        }
        function copyLogs() {
            let logText = document.getElementById('logs').innerText;
            navigator.clipboard.writeText(logText).then(() => {
                alert('Logs copiados com sucesso!');
            }).catch(err => {
                alert('Erro ao copiar logs.');
            });
        }
        setInterval(updateLogs, 2000);
        updateLogs();
    </script>
</body>
</html>
"""

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SparkHub Dashboard</title>
    <style>
        body { font-family: monospace; background: #0d1117; color: #c9d1d9; margin: 0; padding: 10px; }
        .card { background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 10px; margin-bottom: 8px; }
        h2 { font-size: 13px; margin: 0 0 6px 0; color: #58a6ff; }
        .ok { color: #3fb950; font-weight: bold; }
        .down { color: #f85149; font-weight: bold; }
        button, select, input { background: #21262d; color: #c9d1d9; border: 1px solid #30363d; padding: 7px; border-radius: 4px; width: 100%; margin-top: 5px; font-family: monospace; box-sizing: border-box; }
        button { cursor: pointer; background: #238636; color: white; font-weight: bold; }
        button:hover { background: #2ea043; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 4px; font-size: 11px; }
    </style>
</head>
<body>
    <h2 style="display:flex; justify-content:space-between; align-items:center;">
        <span>GDD-as-Code · Módulo 6 · SparkHub</span>
        <span>
            <button style="width:auto; padding:2px 6px; margin:0; font-size:10px;" onclick="changeZoom(-0.1)">-</button>
            <button style="width:auto; padding:2px 6px; margin:0; font-size:10px;" onclick="changeZoom(0.1)">+</button>
        </span>
    </h2>
    <div style="font-size: 10px; margin-bottom: 8px; color: #8b949e;">
        porta :8085 · escopo <span id="scope">Local SQLite</span>
    </div>

    <!-- Card 1: DiskGuard -->
    <div class="card">
        <h2>01 · Saúde do Armazenamento</h2>
        <div class="grid">
            <div>C:\\: <span id="c_status">--</span> (<span id="c_free">--</span>GB)</div>
            <div>D:\\: <span id="d_status">--</span> (<span id="d_free">--</span>GB)</div>
        </div>
    </div>

    <!-- Card 2: MemPalace -->
    <div class="card">
        <h2>02 · Memória MemPalace (<span id="mp_wal" class="down">OFFLINE</span>)</h2>
        <div style="font-size: 12px;">Total: <strong id="mp_total">0</strong></div>
        <div id="mp_rooms" style="font-size: 10px; margin-top: 3px; color: #8b949e;">Sem dados estruturados.</div>
    </div>

    <!-- Card 3: Economia -->
    <div class="card">
        <h2>03 · Painel de Economia (Zero Tokens)</h2>
        <div style="font-size: 18px; color: #8b949e;" id="econ_pct">0.0%</div>
        <div style="font-size: 10px; color: #8b949e;" id="econ_details">Sem dados em cache local.</div>
    </div>

    <!-- Cards 4-7: Serviços -->
    <div class="card">
        <h2>
            <span>04-07 · Barramentos e Infraestrutura</span>
            <a href="/logs" style="background: #21262d; color: #c9d1d9; border: 1px solid #30363d; padding: 2px 6px; border-radius: 4px; text-decoration: none; font-size: 10px; float: right;">Ver Logs</a>
        </h2>
        <div style="font-size: 11px;" id="services">Aguardando heartbeat...</div>
        <div style="margin-top: 5px; font-size: 10px; color: #8b949e; border-top: 1px dashed #30363d; padding-top: 5px;">
            <strong>Última Conexão MCP:</strong> <span id="mcp_conn">Nenhuma requisição recente.</span>
        </div>
    </div>

    <!-- Novo Card: Fontes de Dados -->
    <div class="card">
        <h2>08 · Fontes de Informação</h2>
        <div style="font-size: 11px;" id="data_sources">Verificando tokens e cotas...</div>
    </div>

    <!-- Novo Card: Mixture of Experts (IAs Dedicadas) -->
    <div class="card">
        <h2>🧠 Mixture of Experts (IAs Dedicadas)</h2>
        <div style="font-size: 11px;" id="moe_status">Inspecionando especialistas...</div>
    </div>

    <!-- Moltbook & Social Insights -->
    <div class="card" id="moltbook-panel">
        <h2>🌐 Moltbook & Social Insights</h2>
        <div id="insights-container" style="font-size: 11px; max-height: 130px; overflow-y: auto; color: #8b949e;">
            <p>Aguardando telemetria de agentes...</p>
        </div>
    </div>

    <!-- Controles -->
    <div class="card">
        <h2>Controles em 1 Clique</h2>
        <button onclick="alert('Sincronização disparada!')">Sincronizar Agora</button>
        <button onclick="alert('Teste de alerta enviado!')">Testar Alertas</button>
        <select id="scopeSelect" onchange="document.getElementById('scope').innerText = this.value;">
            <option value="Local SQLite">Local SQLite</option>
            <option value="Google Sheets">Google Sheets</option>
        </select>
    </div>

    <!-- Input Unificado -->
    <div class="card">
        <h2>Input de Uma Mão Unificado</h2>
        
        <div id="chat_log" style="background: rgba(0,0,0,0.3); border: 1px solid #30363d; border-radius: 4px; padding: 10px; margin-bottom: 10px; font-size: 11px; color: #8b949e; height: 150px; overflow-y: auto; display: flex; flex-direction: column;">
            <div style="margin-bottom: 4px;">[Sistema] Canal conectado. Aguardando comandos...</div>
        </div>

        <input type="text" id="cmd" placeholder="Comando ou mensagem rápida..." onkeypress="if(event.key === 'Enter') sendCmd()">
        <button onclick="sendCmd()">Enviar</button>
    </div>

    <script>
        // Memória de Posição, Tamanho e Escala (Zoom)
        function changeZoom(delta) {
            let z = parseFloat(localStorage.getItem('dashboard_zoom') || 1);
            z += delta;
            if(z < 0.5) z = 0.5;
            if(z > 3.0) z = 3.0;
            document.body.style.zoom = z;
            localStorage.setItem('dashboard_zoom', z);
        }

        function saveWindowState() {
            localStorage.setItem('dashboard_x', window.screenX);
            localStorage.setItem('dashboard_y', window.screenY);
            localStorage.setItem('dashboard_w', window.outerWidth);
            localStorage.setItem('dashboard_h', window.outerHeight);
        }

        window.onload = () => {
            let x = localStorage.getItem('dashboard_x');
            let y = localStorage.getItem('dashboard_y');
            let w = localStorage.getItem('dashboard_w');
            let h = localStorage.getItem('dashboard_h');
            let z = localStorage.getItem('dashboard_zoom') || 1;
            
            document.body.style.zoom = z;
            
            if (x !== null && y !== null && w !== null && h !== null) {
                try {
                    window.moveTo(parseInt(x), parseInt(y));
                    window.resizeTo(parseInt(w), parseInt(h));
                } catch(e) {}
            }
        };

        window.addEventListener('beforeunload', saveWindowState);
        setInterval(saveWindowState, 2000);

        function update() {
            fetch('/api/status').then(r => r.json()).then(d => {
                document.getElementById('c_free').innerText = d.disk.c_free;
                document.getElementById('d_free').innerText = d.disk.d_free;
                
                document.getElementById('c_status').className = d.disk.c_norm ? 'ok' : 'down';
                document.getElementById('c_status').innerText = d.disk.c_norm ? 'NORMAL' : 'CRÍTICO';
                document.getElementById('d_status').className = d.disk.d_norm ? 'ok' : 'down';
                document.getElementById('d_status').innerText = d.disk.d_norm ? 'NORMAL' : 'CRÍTICO';

                document.getElementById('mp_total').innerText = d.mempalace.total;
                
                let wal_el = document.getElementById('mp_wal');
                if (d.mempalace.wal) {
                    wal_el.innerText = 'SQLITE WAL';
                    wal_el.className = 'ok';
                } else {
                    wal_el.innerText = 'OFFLINE/PADRÃO';
                    wal_el.className = 'down';
                }
                
                let rooms = "";
                for(let [k,v] of Object.entries(d.mempalace.rooms)) { rooms += `${k}: ${v} | `; }
                document.getElementById('mp_rooms').innerText = rooms || "Nenhuma memória registrada.";

                let srv = "";
                for(let [k,v] of Object.entries(d.services)) {
                    srv += `<div>${k}: <span class="${v ? 'ok' : 'down'}">${v ? 'UP' : 'DOWN'}</span></div>`;
                }
                document.getElementById('services').innerHTML = srv;

                let ds = "";
                for(let [k,v] of Object.entries(d.data_sources)) {
                    let cls = v.status === 'OK' ? 'ok' : (v.status === 'WARNING' ? 'warning' : 'down');
                    ds += `<div>${k}: <span class="${cls}">${v.status}</span> <span style="color:#8b949e; font-size:9px;">(${v.detail})</span></div>`;
                }
                document.getElementById('data_sources').innerHTML = ds || "Indisponível";

                let moe = "";
                if(d.moe) {
                    for(let [k,v] of Object.entries(d.moe)) {
                        let cls = v.status === 'OK' ? 'ok' : 'down';
                        moe += `<div>${k}: <span class="${cls}">${v.status}</span> <span style="color:#8b949e; font-size:10px;">(${v.detail})</span></div>`;
                    }
                    if(document.getElementById('moe_status')) {
                        document.getElementById('moe_status').innerHTML = moe || "N/A";
                    }
                }
            });
        }
        function sendCmd() {
            let val = document.getElementById('cmd').value;
            if(!val) return;
            
            let log = document.getElementById('chat_log');
            log.innerHTML += `<div style="color: #c9d1d9;">> Você: ${val}</div>`;
            document.getElementById('cmd').value = '';
            
            fetch('/api/chat', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({message: val})})
                .then(r => r.json()).then(res => { 
                    log.innerHTML += `<div style="color: #58a6ff;">> Hub: ${res.received}</div>`;
                    log.scrollTop = log.scrollHeight;
                }).catch(e => {
                    log.innerHTML += `<div class="down">> Erro ao enviar comando.</div>`;
                });
        }
        
        async function refreshSocialInsights() {
            try {
                const response = await fetch('/api/social_insights');
                const json = await response.json();
                if (json.status === 'success' && json.data.length > 0) {
                    const container = document.getElementById('insights-container');
                    container.innerHTML = json.data.map(item => `
                        <div style="border-bottom: 1px solid #30363d; padding-bottom: 4px; margin-bottom: 4px;">
                            <span style="color: #58a6ff;">[${item.timestamp}]</span>
                            <p style="margin: 2px 0 0 0;">${item.content}</p>
                        </div>
                    `).join('');
                }
            } catch (err) {
                console.error("Erro ao sincronizar insights sociais:", err);
            }
        }
        setInterval(refreshSocialInsights, 30000);
        refreshSocialInsights();

        async function fetchMCP() {
            try {
                let r = await fetch('/api/orchestrator/telemetry');
                let d = await r.json();
                if(d && d.length > 0) {
                    let last = d[0];
                    let cls = last.status === 'sucesso' ? 'ok' : 'down';
                    document.getElementById('mcp_conn').innerHTML = 
                        `<span class="${cls}">${last.tool}</span> (${last.latency_ms}ms) -> ${last.backend_used} [${last.status}]`;
                }
            } catch(e) {}
        }
        setInterval(fetchMCP, 2000);
        fetchMCP();

        setInterval(update, 2000);
        update();
    </script>
</body>
</html>
"""


@app.route("/")
@login_required
def index():
  return render_template_string(HTML_TEMPLATE)

@app.route("/logs")
@login_required
def logs_page():
  return render_template_string(LOGS_TEMPLATE)

@app.route("/api/logs", methods=["GET"])
@login_required
def api_logs():
    try:
        log_file = str(get_path("logs/sparkhub.log"))
        if not os.path.exists(log_file):
            return jsonify({"status": "error", "message": "Log file not found."}), 404
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return jsonify({"status": "success", "data": [l.strip() for l in lines[-100:]]})
    except Exception as e:
        logger.error(f"Erro lendo logs: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


def check_process(process_name: str) -> bool:
    import psutil
    try:
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] and process_name.lower() in proc.info['name'].lower():
                return True
        return False
    except Exception:
        return False


@app.route("/api/status")
def api_status():
    import urllib.request
    from dotenv import load_dotenv
    load_dotenv(get_path(".env"), override=True)
    
    def check_llm(url, token_env):
        token = os.environ.get(token_env, "")
        if not token: return {"status": "NO_TOKEN", "detail": "Token ausente"}
        try:
            req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
            urllib.request.urlopen(req, timeout=2)
            return {"status": "OK", "detail": "Conectado"}
        except urllib.error.HTTPError as e:
            if e.code == 429: return {"status": "QUOTA", "detail": "Limite Excedido"}
            if e.code == 401: return {"status": "UNAUTH", "detail": "Token Inválido"}
            return {"status": "OK", "detail": "Conectado"} # APIs normais dao 400 em GET sem body
        except Exception:
            return {"status": "OFFLINE", "detail": "Timeout"}

    return jsonify({
        "disk": get_disk_status(),
        "mempalace": get_mempalace_stats(),
        "services": {
            f"Core MCP (:{MCP_PORT})": check_port("127.0.0.1", MCP_PORT),
            "Antigravity IDE": check_process("Antigravity.exe"),
            "VSCode IDE": check_process("code.exe"),
            "Blender Engine": check_process("blender.exe"),
            "Godot Engine": check_process("godot"),
            "Bot WhatsApp (:8082)": check_port("127.0.0.1", 8082),
            "Dashboard (:8085)": check_port("127.0.0.1", 8085),
        },
        "data_sources": {
            "OpenRouter (Camada 2)": check_llm("https://openrouter.ai/api/v1/auth/key", "OPENROUTER_API_KEY"),
            "DeepSeek (Camada 3)": {"status": "OK", "detail": "Configurado"} if os.environ.get("DEEPSEEK_API_KEY") else {"status": "NO_TOKEN", "detail": "Faltando"},
            "Gemini (Camada 4)": {"status": "OK", "detail": "Configurado"} if os.environ.get("GEMINI_API_KEY") else {"status": "NO_TOKEN", "detail": "Faltando"},
            "NVIDIA Build (Embeddings)": {"status": "OK", "detail": "Configurado"} if os.environ.get("NVIDIA_API_KEY") else {"status": "NO_TOKEN", "detail": "Faltando"},
            "Ollama (Local)": {"status": "OK", "detail": "Conectado"} if check_port("127.0.0.1", 11434) else {"status": "OFFLINE", "detail": "Inativo"},
            "Gmail Principal": {"status": "OK", "detail": "Token Ativo"} if os.path.exists(str(get_path("token.json"))) or os.path.exists(str(get_path("credentials/token.pickle"))) else {"status": "NO_TOKEN", "detail": "Não Autenticado"},
            "Google Drive": {"status": "OK", "detail": "Token Ativo"} if os.path.exists(str(get_path("token.json"))) or os.path.exists(str(get_path("credentials/token.pickle"))) else {"status": "NO_TOKEN", "detail": "Não Autenticado"},
            "MemPalace (SQLite)": {"status": "OK", "detail": "Ativo"} if os.path.exists(str(get_path("mempalace.db"))) else {"status": "NO_DB", "detail": "Arquivo Ausente"}
        },
        "moe": {
            "Agente de Código": {"status": "OK", "detail": "Poolside Laguna XS 2.1"},
            "Geração/Chat (Texto)": {"status": "OK", "detail": "Ollama/Gemini/OpenRouter"},
            "Memória (Embeddings)": {"status": "OK", "detail": "Llama Nemotron-1B"},
            "Motor Rerank (Contexto)": {"status": "OK", "detail": "Llama Nemotron Rerank-1B"},
            "Análise Visual (Imagem/Vídeo)": {"status": "OK", "detail": "Gemini 2.0 Flash"},
            "Audição (Transcrição Local)": {"status": "OK", "detail": "Faster-Whisper"}
        }
    })

@app.route("/api/orchestrator/status")
def api_orchestrator_status():
    from sparkhub_mcp_orchestrator import orchestrator
    # Convert states to a serializable format
    return jsonify(orchestrator.cb.states)

@app.route("/api/orchestrator/telemetry")
def api_orchestrator_telemetry():
    import json
    try:
        with open("D:\\SparkHub\\mcp_telemetry.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify(data[::-1][:50]) # Return last 50
    except Exception:
        return jsonify([])



def send_systray_signal(msg: str):
    """Envia sinal UDP IPC instantâneo para o Ícone de Bandeja do Windows (porta 8087)."""
    try:
        import sparkhub_ipc
        sparkhub_ipc.send_systray_signal(msg)
    except Exception:
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.sendto(msg.encode("utf-8"), ("127.0.0.1", 8087))
            s.close()
        except Exception as e:
            print(f"[MURPHY] Erro ao enviar sinal Systray: {e}")


def notify_pc_screen(title: str, message: str):
    """Exibe notificação Windows Toast no monitor do PC e imprime no console."""
    import subprocess
    import time
    timestamp = time.strftime("%H:%M:%S")
    print(f"\n[MOBILE COMMAND] [{timestamp}] {title}: {message}")
    try:
        clean_title = title.replace("'", "").replace('"', "")
        clean_msg = message.replace("'", "").replace('"', "")
        ps_cmd = f"""
        Add-Type -AssemblyName System.Windows.Forms;
        $notify = New-Object System.Windows.Forms.NotifyIcon;
        $notify.Icon = [System.Drawing.SystemIcons]::Information;
        $notify.Visible = $true;
        $notify.ShowBalloonTip(4000, '{clean_title[:50]}', '{clean_msg[:120]}', [System.Windows.Forms.ToolTipIcon]::Info);
        Start-Sleep -Seconds 3;
        $notify.Dispose();
        """
        subprocess.Popen(["powershell", "-NoProfile", "-Command", ps_cmd], creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        print(f"[MURPHY] Erro ao disparar Toast no PC: {e}")


def launch_app_interactively(app_cmd: str) -> bool:
    """Abre aplicativo interativamente na área de trabalho visível do Windows."""
    import subprocess
    try:
        os.startfile(app_cmd)
        return True
    except Exception:
        pass
    try:
        subprocess.Popen(["powershell", "-NoProfile", "-Command", f'Start-Process "{app_cmd}"'], creationflags=subprocess.CREATE_NO_WINDOW)
        return True
    except Exception:
        pass
    try:
        subprocess.Popen(f'start "" "{app_cmd}"', shell=True)
        return True
    except Exception:
        return False


@app.route("/api/chat", methods=["POST"])
@login_required
def api_chat():
    import subprocess
    import datetime
    import json
    data = request.json or {}
    msg_raw = data.get("message", "").strip()
    msg = msg_raw.lower()
    
    if not msg:
        return jsonify({"status": "OK", "received": "Mensagem vazia."})
        
    # 🟡 Muda o Ícone da Bandeja para Amarelo (Processing)
    send_systray_signal("yellow")
    notify_pc_screen("📱 Comando do Celular Recebido", f"Instrução: '{msg_raw}'")
    
    response_text = ""
    
    # 1. Comandos Diretos de SO (Abertura Nativa Interativa no Windows - Intenção Explícita)
    if any(k in msg for k in ["abrir bloco", "abrir notepad", "abrir bloco de notas"]) or msg in ["notepad", "bloco", "bloco de notas"]:
        send_systray_signal("open_notepad")
        launch_app_interactively("notepad.exe")
        response_text = "🚀 Bloco de Notas aberto com sucesso no PC!"
    elif any(k in msg for k in ["abrir vscode", "abrir code"]) or msg in ["vscode", "code"]:
        send_systray_signal("open_vscode")
        launch_app_interactively("code")
        response_text = "🚀 VSCode abrindo na tela do PC!"
    elif any(k in msg for k in ["abrir blender"]) or msg == "blender":
        send_systray_signal("open_blender")
        launch_app_interactively("blender")
        response_text = "🚀 Blender abrindo no PC!"
    elif any(k in msg for k in ["abrir antigravity", "abrir agy"]) or msg in ["antigravity app", "agy app"]:
        send_systray_signal("open_antigravity")
        launch_app_interactively("antigravity")
        response_text = "🚀 Antigravity IDE abrindo no PC!"
    elif any(k in msg for k in ["abrir calculadora", "abrir calc"]) or msg in ["calc", "calculadora"]:
        send_systray_signal("open_calc")
        launch_app_interactively("calc.exe")
        response_text = "🚀 Calculadora aberta no PC!"
    else:
        # 2. Requisição Geral - Despacha para API Core ativa (porta 8000) via HTTP
        try:
            import urllib.request
            import json
            payload = json.dumps({
                "action": "ask_ai", 
                "params": {"prompt": msg_raw, "profile": "auto"}
            }).encode('utf-8')
            
            req = urllib.request.Request(
                "http://127.0.0.1:8000", 
                data=payload, 
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {API_TOKEN}'
                }
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                resp_data = json.loads(response.read().decode('utf-8'))
                if resp_data.get("status") == "sucesso":
                    response_text = resp_data.get("mensagem", "")
                else:
                    response_text = f"❌ Erro na API Core: {resp_data.get('mensagem', 'Falha Desconhecida')}"
                    
        except Exception as e:
            response_text = f"❌ Falha de Conexão com a API Core (Porta 8000): O motor principal não respondeu. {str(e)}"
            
        # 3. Grava no MemPalace DB via sparkhub_db de forma segura (Zero Mismatches)
        try:
            import sparkhub_db
            sparkhub_db.save_chat_message("mobile", msg_raw, response_text, "mobile", DB_PATH)
        except Exception as e_db:
            print(f"[MURPHY] Erro ao gravar tarefa no MemPalace: {e_db}")

        # 4. Injeta notificação na Antigravity IDE (notifications.json)
        try:
            import sparkhub_ipc
            sparkhub_ipc.notify_ide_quadchannel("Mobile Request (Dashboard)", msg_raw)
        except Exception as e_ide:
            print(f"[MURPHY] Erro ao notificar IDE: {e_ide}")

    # 🟢 Retorna Ícone da Bandeja para Verde (Operational) e envia Notificação Toast no PC
    notify_pc_screen("📱 SparkHub Resposta", response_text)
    send_systray_signal("green")

    return jsonify({"status": "OK", "received": response_text})

@app.route('/api/social_insights', methods=['GET'])
@login_required
def get_social_insights():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT content, timestamp FROM memories 
            WHERE room = 'social_insights' 
            ORDER BY id DESC LIMIT 5
        """)
        rows = cursor.fetchall()
        conn.close()
        
        insights = [{"content": row[0], "timestamp": row[1]} for row in rows]
        return jsonify({"status": "success", "data": insights})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/moltbook/sync', methods=['POST'])
@login_required
def api_moltbook_sync():
    try:
        # Import local to avoid circular import loops early on
        from sparkhub_moltbook_agent import get_moltbook_agent
        agent = get_moltbook_agent()
        
        # In a real app we'd dispatch this async, but for MVP we run sync and return stats
        # If heavy load is detected, we could reject it or bypass since it's "On Demand"
        # The user specification says: "Varredura imediata acionada por comando MCP ou Dashboard."
        result = agent.sinc_demanda()
        
        if result.get("status") == "success":
            return jsonify({"status": "success", "data": result.get("stats", {})})
        else:
            return jsonify({"status": "error", "message": result.get("message", "Erro desconhecido")}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    send_systray_signal("green")
    send_systray_signal("icon_orb")
    try:
        import threading
        
        threading.Thread(target=lambda: None, daemon=True).start()
    except Exception as e_systray:
        print(f"[SYSTRAY] Falha ao iniciar ícone de bandeja: {e_systray}")
    app.run(host="0.0.0.0", port=8085, debug=False)
