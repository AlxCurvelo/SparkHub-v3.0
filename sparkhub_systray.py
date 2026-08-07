# sparkhub_systray.py
# SparkHub v3.0 - Widget de Status Premium (Arrastável, Redimensionável e Persistente)
# 🟢 Verde: Operacional | 🟡 Amarelo: Processando | 🔴 Vermelho: Offline

import os
import socket
import sys
import threading
import time
import json
import tkinter as tk
import ctypes

BASE_DIR         = os.path.dirname(os.path.abspath(__file__))
LOG_FILE         = os.path.join(BASE_DIR, "systray.log")
f_log = open(LOG_FILE, "a", encoding="utf-8")
sys.stdout = f_log
sys.stderr = f_log

import traceback
def global_exception_handler(exc_type, exc_value, exc_traceback):
    with open(r'D:\SparkHub\systray_fatal.log', 'w') as f:
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
sys.excepthook = global_exception_handler
SYSTRAY_UDP_PORT = 8087
DASHBOARD_URL    = "http://127.0.0.1:8085"
BASE_DIR         = os.path.dirname(os.path.abspath(__file__))
LOG_FILE         = os.path.join(BASE_DIR, "systray.log")
CONFIG_FILE      = os.path.join(BASE_DIR, "systray_config.json")

# Previne múltiplas instâncias do widget
mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "SparkHubSystrayMutex_v3")
if ctypes.windll.kernel32.GetLastError() == 183: # ERROR_ALREADY_EXISTS
    print("[SYSTRAY] Uma instância já está rodando. Encerrando.")
    sys.exit(0)

BASE_DIR         = os.path.dirname(os.path.abspath(__file__))
LOG_FILE         = os.path.join(BASE_DIR, "systray.log")
CONFIG_FILE      = os.path.join(BASE_DIR, "systray_config.json")

try:
    _lf = open(LOG_FILE, "w", encoding="utf-8", buffering=1)
    sys.stdout = _lf
    sys.stderr = _lf
except Exception:
    pass

dashboard_proc = None

print(f"[SYSTRAY] Iniciando... Python {sys.version.split()[0]}")

# ─────────────────────────────────────────────
# CONFIGURAÇÕES DE PERSISTÊNCIA
# ─────────────────────────────────────────────
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"[SYSTRAY] Erro ao carregar config: {e}")
    return {}

def save_config(x, y, w, h):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump({"x": x, "y": y, "w": w, "h": h}, f)
        print(f"[SYSTRAY] Configurações salvas: {w}x{h} em {x},{y}")
    except Exception as e:
        print(f"[SYSTRAY] Erro ao salvar config: {e}")

# ─────────────────────────────────────────────
# VARIÁVEIS DE ESTADO DO ARRASTE
# ─────────────────────────────────────────────
drag_data = {"x": 0, "y": 0, "w": 0, "h": 0, "dragging": False, "resizing": False}

# ─────────────────────────────────────────────
# PALETA DE CORES
# ─────────────────────────────────────────────
COLORS = {
    "green":  {"bg": "#22c55e", "hi": "#86efac", "dim": "#15803d", "text": "Operacional",   "accent": "#16a34a"},
    "yellow": {"bg": "#f59e0b", "hi": "#fcd34d", "dim": "#b45309", "text": "Processando...", "accent": "#d97706"},
    "red":    {"bg": "#ef4444", "hi": "#fca5a5", "dim": "#b91c1c", "text": "Offline",        "accent": "#dc2626"},
}

# UI globals
current_state = "green"
root          = None
canvas        = None
status_label  = None
accent_bar    = None
pulse_canvas  = None
resize_grip   = None
pulse_step    = 0
pulse_dir     = 1

# ─────────────────────────────────────────────
# DESENHA ÍCONE CIRCULAR
# ─────────────────────────────────────────────
def draw_circle(state: str):
    if canvas is None:
        return
    c  = COLORS.get(state, COLORS["green"])
    sz = 21
    canvas.config(width=sz, height=sz)
    canvas.delete("all")
    m  = 1
    # Sombra
    canvas.create_oval(m+1, m+1, sz-m, sz-m, fill="#06060f", outline="")
    # Anel externo (glow)
    canvas.create_oval(m, m, sz-m, sz-m, fill=c["dim"], outline=c["bg"], width=1)
    # Círculo principal
    canvas.create_oval(m+2, m+2, sz-m-2, sz-m-2, fill=c["bg"], outline="")
    # Brilho
    canvas.create_oval(m+5, m+3, sz-m-7, sz-m-9, fill=c["hi"], outline="")

# ─────────────────────────────────────────────
# DOT ANIMADO (pulso)
# ─────────────────────────────────────────────
def animate_pulse():
    global pulse_step, pulse_dir
    if pulse_canvas is None or root is None:
        return
    c = COLORS.get(current_state, COLORS["green"])
    pulse_step += pulse_dir * 2
    if pulse_step >= 12 or pulse_step <= 0:
        pulse_dir *= -1
    r = 2 + (pulse_step / 12) * 1.5
    pulse_canvas.delete("all")
    cx, cy = 4, 4
    # Glow
    pulse_canvas.create_oval(cx-r-1, cy-r-1, cx+r+1, cy+r+1, fill=c["dim"], outline="")
    # Dot sólido
    pulse_canvas.create_oval(cx-2, cy-2, cx+2, cy+2, fill=c["bg"], outline=c["hi"], width=1)
    root.after(55, animate_pulse)

# ─────────────────────────────────────────────
# APLICAR ESTADO NA UI
# ─────────────────────────────────────────────
def _apply_state(state: str):
    c = COLORS.get(state, COLORS["green"])
    draw_circle(state)
    if status_label:
        status_label.config(text=c["text"], fg=c["hi"])
    if accent_bar:
        accent_bar.config(bg=c["accent"])
    if resize_grip:
        resize_grip.config(bg=c["dim"])
    if root:
        root.title(f"SparkHub — {c['text']}")

def set_state(state: str):
    global current_state
    if state not in COLORS:
        state = "green"
    current_state = state
    print(f"[SYSTRAY] Estado → {state.upper()}")
    if root:
        root.after(0, lambda: _apply_state(state))

# ─────────────────────────────────────────────
# APPS
# ─────────────────────────────────────────────
def open_app(name: str):
    global dashboard_proc
    import subprocess, webbrowser, socket, time
    try:
        if name == "dashboard":
            try:
                import win32gui
                hwnds = []
                def callback(hwnd, extra):
                    if win32gui.IsWindowVisible(hwnd):
                        title = win32gui.GetWindowText(hwnd)
                        if "SparkHub Dashboard" in title:
                            hwnds.append(hwnd)
                win32gui.EnumWindows(callback, None)
                if hwnds:
                    print("[SYSTRAY] Dashboard popup já está aberto. Trazendo para a frente.")
                    # 9 = SW_RESTORE
                    import win32con
                    win32gui.ShowWindow(hwnds[0], win32con.SW_RESTORE)
                    win32gui.SetForegroundWindow(hwnds[0])
                    return
            except Exception as e:
                print(f"[SYSTRAY] Falha ao verificar janela: {e}")
            
            # Auto-healing: Verifica se o dashboard está rodando
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            try:
                s.connect(("127.0.0.1", 8085))
                s.close()
            except:
                print("[SYSTRAY] Dashboard offline! Auto-healing iniciado...")
                subprocess.Popen(["cmd.exe", "/c", r"D:\SparkHub\iniciar_backend.bat"], creationflags=subprocess.CREATE_NO_WINDOW)
                time.sleep(6) # Aguarda os serviços subirem

            EDGE   = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
            CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            APP_FLAGS = [
                f"--app={DASHBOARD_URL}",
                "--window-size=480,820",
                "--window-position=100,100",
                "--no-first-run",
                "--disable-extensions",
            ]
            launched = False
            for browser_path in (EDGE, CHROME):
                if os.path.exists(browser_path):
                    print(f"[SYSTRAY] Abrindo dashboard popup via {os.path.basename(browser_path)}")
                    dashboard_proc = subprocess.Popen([browser_path] + APP_FLAGS)
                    launched = True
                    break
            if not launched:
                print("[SYSTRAY] Navegador não encontrado, usando webbrowser padrão")
                webbrowser.open(DASHBOARD_URL)
        elif name == "powershell":
            subprocess.Popen(["cmd.exe", "/c", "start", "powershell.exe", "-NoExit", "-Command", "cd D:\\SparkHub"])
        print(f"[SYSTRAY] Abriu: {name}")
    except Exception as e:
        print(f"[SYSTRAY] Erro ao abrir {name}: {e}")

# ─────────────────────────────────────────────
# ÍCONE METAMÓRFICO DE ÁREA DE TRABALHO
# ─────────────────────────────────────────────
def change_desktop_icon(icon_type):
    try:
        desktop = os.path.join(os.environ['USERPROFILE'], 'OneDrive', 'Desktop')
        if not os.path.exists(desktop):
            desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
        lnk_path = os.path.join(desktop, 'SparkHub v3.0.lnk')
        if not os.path.exists(lnk_path):
            return
            
        icon_file = f"{icon_type}.ico"
        icon_path = os.path.join(BASE_DIR, "ico", icon_file)
        
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(lnk_path)
        shortcut.IconLocation = icon_path
        shortcut.save()
        
        SHCNE_ASSOCCHANGED = 0x08000000
        SHCNF_IDLIST = 0x0000
        ctypes.windll.shell32.SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, None, None)
        print(f"[SYSTRAY] Ícone metamórfico alterado para {icon_type}")
    except Exception as e:
        print(f"[SYSTRAY] Falha ao alterar ícone: {e}")

# ─────────────────────────────────────────────
# UDP IPC SERVER
# ─────────────────────────────────────────────
def udp_server():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", SYSTRAY_UDP_PORT))
        print(f"[SYSTRAY] UDP ativo na porta {SYSTRAY_UDP_PORT}")
    except Exception as e:
        print(f"[SYSTRAY] Falha UDP: {e}")
        return

    while True:
        try:
            data, _ = sock.recvfrom(2048)
            raw = data.decode("utf-8", errors="ignore").strip()
            
            cmd = ""
            if raw.startswith("{"):
                try:
                    payload = json.loads(raw)
                    cmd = payload.get("cmd", "").lower()
                except:
                    cmd = raw.lower()
            else:
                cmd = raw.lower()

            if cmd in ("green", "yellow", "red"):
                set_state(cmd)
            elif cmd.startswith("icon_"):
                icon_type = cmd.split("_")[1]
                change_desktop_icon(icon_type)
            elif cmd.startswith("open_"):
                app = cmd[5:]
                set_state("yellow")
                threading.Thread(target=open_app, args=(app,), daemon=True).start()
                time.sleep(1.5)
                set_state("green")
        except Exception as e:
            time.sleep(0.3)

# ─────────────────────────────────────────────
# INTERAÇÕES DO MOUSE E MENU
# ─────────────────────────────────────────────
def show_menu(event):
    m = tk.Menu(root, tearoff=0, bg="#0f0f1e", fg="#c8c8f0", activebackground="#252545",
                activeforeground="#ffffff", relief="flat", borderwidth=1, font=("Segoe UI", 10))
    m.add_command(label="  🌐  Abrir Dashboard",  foreground="#00ffff", command=lambda: open_app("dashboard"))
    m.add_command(label="  ⚡  Terminal PowerShell", foreground="#ff00ff", command=lambda: open_app("powershell"))
    m.add_separator()
    m.add_command(label="  🟢  Operacional",      foreground="#00ff00", command=lambda: set_state("green"))
    m.add_command(label="  🟡  Processando",      foreground="#ffff00", command=lambda: set_state("yellow"))
    m.add_command(label="  🔴  Offline",          foreground="#ff4444", command=lambda: set_state("red"))
    m.add_separator()
    m.add_command(label="  ❌  Sair",             foreground="#aaaaaa", command=root.quit)
    m.tk_popup(event.x_root, event.y_root)

# Funções de Arrasto (Move)
def start_move(event):
    if event.widget == resize_grip: return
    drag_data["x"] = event.x
    drag_data["y"] = event.y
    drag_data["dragging"] = True

def do_move(event):
    if drag_data["dragging"]:
        deltax = event.x - drag_data["x"]
        deltay = event.y - drag_data["y"]
        x = root.winfo_x() + deltax
        y = root.winfo_y() + deltay
        root.geometry(f"+{x}+{y}")

def stop_move(event):
    if drag_data["dragging"]:
        drag_data["dragging"] = False
        save_config(root.winfo_x(), root.winfo_y(), root.winfo_width(), root.winfo_height())

# Funções de Redimensionamento (Resize)
def start_resize(event):
    drag_data["x"] = event.x_root
    drag_data["y"] = event.y_root
    drag_data["w"] = root.winfo_width()
    drag_data["h"] = root.winfo_height()
    drag_data["resizing"] = True

def do_resize(event):
    if drag_data["resizing"]:
        deltax = event.x_root - drag_data["x"]
        deltay = event.y_root - drag_data["y"]
        new_w = max(115, drag_data["w"] + deltax)
        new_h = max(31, drag_data["h"] + deltay)
        root.geometry(f"{new_w}x{new_h}")

def stop_resize(event):
    if drag_data["resizing"]:
        drag_data["resizing"] = False
        save_config(root.winfo_x(), root.winfo_y(), root.winfo_width(), root.winfo_height())

def on_enter(e):
    if root: root.attributes("-alpha", 1.0)
def on_leave(e):
    if root: root.attributes("-alpha", 0.90)

# ─────────────────────────────────────────────
# MAIN – WIDGET PREMIUM
# ─────────────────────────────────────────────
def main():
    global root, canvas, status_label, accent_bar, pulse_canvas, resize_grip

    threading.Thread(target=udp_server, daemon=True).start()

    root = tk.Tk()
    root.title("SparkHub v3.0")
    try:
        root.iconbitmap(r"D:\SparkHub\ico\core.ico")
    except:
        pass
    root.resizable(False, False)
    root.attributes("-topmost", True)
    root.attributes("-alpha", 0.90)
    root.overrideredirect(True)

    # Coordenadas Iniciais Padrão (canto inferior direito)
    WIN_W, WIN_H = 115, 31
    try:
        import ctypes as _ct
        _u = _ct.windll.user32
        pw, ph = _u.GetSystemMetrics(0), _u.GetSystemMetrics(1)
    except Exception:
        pw, ph = 1920, 1080
    x = pw - WIN_W - 7
    y = ph - WIN_H - 25

    # Sobrescreve com configuração salva, se houver
    cfg = load_config()
    if cfg:
        x = cfg.get("x", x)
        y = cfg.get("y", y)
        WIN_W = cfg.get("w", WIN_W)
        WIN_H = cfg.get("h", WIN_H)

    root.geometry(f"{WIN_W}x{WIN_H}+{x}+{y}")
    print(f"[SYSTRAY] Inicial: {WIN_W}x{WIN_H} em {x},{y}")

    BG, BG2, BORD = "#0e0e20", "#12122a", "#2a2a50"
    root.configure(bg=BORD)

    card = tk.Frame(root, bg=BG, bd=0)
    card.pack(fill="both", expand=True, padx=1, pady=1)

    accent_bar = tk.Frame(card, bg=COLORS["green"]["accent"], height=2)
    accent_bar.pack(side="top", fill="x")

    body = tk.Frame(card, bg=BG)
    body.pack(fill="both", expand=True, padx=4, pady=2)

    canvas = tk.Canvas(body, width=21, height=21, bg=BG, highlightthickness=0)
    canvas.pack(side="left", padx=(0, 4))

    info_frame = tk.Frame(body, bg=BG)
    info_frame.pack(side="left", fill="both", expand=True)

    title_frame = tk.Frame(info_frame, bg=BG)
    title_frame.pack(anchor="w")
    tk.Label(title_frame, text="SPARKHUB", font=("Segoe UI", 6, "bold"), fg="#818cf8", bg=BG).pack(side="left")
    tk.Label(title_frame, text=" v3.0", font=("Segoe UI", 5), fg="#475569", bg=BG).pack(side="left")

    status_label = tk.Label(info_frame, text=COLORS["green"]["text"], font=("Segoe UI", 7, "bold"), fg=COLORS["green"]["hi"], bg=BG)
    status_label.pack(anchor="w")

    pulse_frame = tk.Frame(body, bg=BG)
    pulse_frame.pack(side="right", padx=(2, 0))

    pulse_canvas = tk.Canvas(pulse_frame, width=8, height=8, bg=BG, highlightthickness=0)
    pulse_canvas.pack()

    # Grip de redimensionamento no canto inferior direito
    resize_grip = tk.Frame(root, bg=COLORS["green"]["dim"], width=8, height=8, cursor="size_nw_se")
    resize_grip.place(relx=1.0, rely=1.0, anchor="se")

    # Bindings Globais
    for widget in (root, card, body, info_frame, title_frame, status_label, canvas, pulse_canvas):
        widget.bind("<Button-3>", show_menu)
        widget.bind("<Double-Button-1>", lambda e: open_app("dashboard"))
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
        
        # Bindings de Arraste (Move)
        widget.bind("<ButtonPress-1>", start_move)
        widget.bind("<B1-Motion>", do_move)
        widget.bind("<ButtonRelease-1>", stop_move)

    # Bindings de Resize (somente no grip)
    resize_grip.bind("<ButtonPress-1>", start_resize)
    resize_grip.bind("<B1-Motion>", do_resize)
    resize_grip.bind("<ButtonRelease-1>", stop_resize)
    resize_grip.bind("<Enter>", lambda e: root.attributes("-alpha", 1.0))
    resize_grip.bind("<Leave>", lambda e: root.attributes("-alpha", 0.90))

    draw_circle("green")
    animate_pulse()
    print("[SYSTRAY] ✅ Widget premium interativo ativo!")
    root.mainloop()

if __name__ == "__main__":
    main()
