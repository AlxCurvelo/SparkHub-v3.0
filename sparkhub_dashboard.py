# C1-CONCEPCAO: Dashboard minimalista e auto-adaptativo (Porta 8085)
# OBJETIVO: Servidor unificado com auto-descoberta de servicos, cards em tempo real e input de uma mao.
# ESCOPOS: 1. API de Status e Healthcheck 2. Interface Responsiva Embed 3. Endpoint de Comando Modular
import os
import shutil
import sqlite3
import time
from flask import Flask, jsonify, render_template_string, request

from sparkhub_paths import get_default_port, get_path

app = Flask(__name__)

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


def get_mempalace_stats():
  # POLITICA ANTI-MOCKS: Valores reais extraídos do DB ou 0 em caso de falha/inexistência.
  if not os.path.exists(DB_PATH):
    return {
        "total": 0,
        "wal": False,
        "rooms": {}
    }
  try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA journal_mode;")
    wal = cursor.fetchone()[0].upper() == "WAL"
    
    cursor.execute("SELECT COUNT(*) FROM memories")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT room, COUNT(*) FROM memories GROUP BY room")
    rooms_data = cursor.fetchall()
    rooms = {str(row[0]): int(row[1]) for row in rooms_data}
    
    conn.close()
    return {
        "total": total,
        "wal": wal,
        "rooms": rooms
    }
  except Exception as e:
    print(f"[MURPHY] Erro ao ler mempalace.db: {e}")
    return {
        "total": 0,
        "wal": False,
        "rooms": {}
    }


# --- C3-EXECUCAO: Template UI Mobile-First ---
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
    <h2>GDD-as-Code · Módulo 6 · SparkHub</h2>
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
        <h2>04-07 · Barramentos e Serviços</h2>
        <div style="font-size: 11px;" id="services">Aguardando heartbeat...</div>
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

        setInterval(update, 2000);
        update();
    </script>
</body>
</html>
"""


@app.route("/")
def index():
  return render_template_string(HTML_TEMPLATE)


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
    return jsonify({
        "disk": get_disk_status(),
        "mempalace": get_mempalace_stats(),
        "services": {
            f"Core MCP (:{MCP_PORT})": check_port("127.0.0.1", MCP_PORT),
            "Antigravity IDE": check_process("Antigravity.exe"),
            "VSCode IDE": check_process("code.exe"),
            "Blender Engine": check_process("blender.exe"),
            "Bot WhatsApp (:8082)": check_port("127.0.0.1", 8082),
            "Godot UDP (:9000)": check_port("127.0.0.1", 9000),
            "OBS WS (:4455)": check_port("127.0.0.1", 4455),
            "Dashboard (:8085)": check_port("127.0.0.1", 8085),
        },
    })


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
        # 2. Requisição Geral / Solicitação de Atualização
        try:
            # Importa dinamicamente a Tríplice Cascata de IA
            import app as core_app
            ai_response = core_app.route_ai_request(msg_raw)
            response_text = ai_response
        except Exception as e:
            response_text = f"🤖 SparkHub: Requisição recebida! ({msg_raw})"
            
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

if __name__ == "__main__":
    send_systray_signal("green")
    try:
        import threading
        import sparkhub_systray
        threading.Thread(target=sparkhub_systray.run_systray, daemon=True).start()
    except Exception as e_systray:
        print(f"[SYSTRAY] Falha ao iniciar ícone de bandeja: {e_systray}")
    app.run(host="0.0.0.0", port=8085, debug=False)
