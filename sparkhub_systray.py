# sparkhub_systray.py
# SparkHub v3.0 - Widget de Status Premium
# 🟢 Verde: Operacional | 🟡 Amarelo: Processando | 🔴 Vermelho: Offline

import os
import socket
import sys
import threading
import time
import json
import tkinter as tk

# ─────────────────────────────────────────────
SYSTRAY_UDP_PORT = 8087
DASHBOARD_URL    = "http://127.0.0.1:8085"
LOG_FILE         = os.path.join(os.path.dirname(os.path.abspath(__file__)), "systray.log")

try:
    _lf = open(LOG_FILE, "w", encoding="utf-8", buffering=1)
    # sys.stdout = _lf
    # sys.stderr = _lf
except Exception:
    pass

print(f"[SYSTRAY] Iniciando... Python {sys.version.split()[0]}")

try:
    from PIL import Image, ImageDraw, ImageTk
    HAS_PIL = True
    print("[SYSTRAY] Pillow OK")
except ImportError:
    HAS_PIL = False

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
    canvas.create_oval(m+1, m+1, sz-m, sz-m,
                       fill="#06060f", outline="")
    # Anel externo (glow)
    canvas.create_oval(m, m, sz-m, sz-m,
                       fill=c["dim"], outline=c["bg"], width=1)
    # Círculo principal
    canvas.create_oval(m+2, m+2, sz-m-2, sz-m-2,
                       fill=c["bg"], outline="")
    # Brilho
    canvas.create_oval(m+5, m+3, sz-m-7, sz-m-9,
                       fill=c["hi"], outline="")


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
    pulse_canvas.create_oval(cx-r-1, cy-r-1, cx+r+1, cy+r+1,
                              fill=c["dim"], outline="")
    # Dot sólido
    pulse_canvas.create_oval(cx-2, cy-2, cx+2, cy+2,
                              fill=c["bg"], outline=c["hi"], width=1)

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
    import subprocess, webbrowser
    try:
        if name == "dashboard":
            webbrowser.open(DASHBOARD_URL)
        elif name == "notepad":
            os.startfile("notepad.exe")
        elif name == "calc":
            os.startfile("calc.exe")
        elif name == "vscode":
            subprocess.Popen(
                ["powershell", "-NoProfile", "-Command", 'Start-Process "code"'],
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        print(f"[SYSTRAY] Abriu: {name}")
    except Exception as e:
        print(f"[SYSTRAY] Erro ao abrir {name}: {e}")


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
            print(f"[SYSTRAY] RAW UDP: '{raw}'")
            
            cmd = ""
            if raw.startswith("{"):
                try:
                    payload = json.loads(raw)
                    cmd = payload.get("cmd", "").lower()
                except Exception:
                    cmd = raw.lower()
            else:
                cmd = raw.lower()

            print(f"[SYSTRAY] CMD PARSED: '{cmd}'")

            if cmd in ("green", "yellow", "red"):
                set_state(cmd)
            elif cmd.startswith("open_"):
                app = cmd[5:]
                set_state("yellow")
                threading.Thread(target=open_app, args=(app,), daemon=True).start()
                time.sleep(1.5)
                set_state("green")
            elif cmd == "ping":
                print("[SYSTRAY] PONG!")
        except Exception as e:
            print(f"[SYSTRAY] Erro UDP: {e}")
            time.sleep(0.3)


# ─────────────────────────────────────────────
# MENU DE CONTEXTO
# ─────────────────────────────────────────────
def show_menu(event):
    m = tk.Menu(root, tearoff=0,
                bg="#0f0f1e", fg="#c8c8f0",
                activebackground="#252545",
                activeforeground="#ffffff",
                relief="flat", borderwidth=1,
                font=("Segoe UI", 10))
    m.add_command(label="  🌐  Abrir Dashboard",  command=lambda: open_app("dashboard"))
    m.add_command(label="  📝  Bloco de Notas",   command=lambda: open_app("notepad"))
    m.add_command(label="  💻  VSCode",           command=lambda: open_app("vscode"))
    m.add_separator()
    m.add_command(label="  🟢  Operacional",      command=lambda: set_state("green"))
    m.add_command(label="  🟡  Processando",      command=lambda: set_state("yellow"))
    m.add_command(label="  🔴  Offline",          command=lambda: set_state("red"))
    m.add_separator()
    m.add_command(label="  ❌  Sair",             command=root.quit)
    m.tk_popup(event.x_root, event.y_root)


# ─────────────────────────────────────────────
# HOVER
# ─────────────────────────────────────────────
def on_enter(e):
    if root:
        root.attributes("-alpha", 1.0)

def on_leave(e):
    if root:
        root.attributes("-alpha", 0.90)


# ─────────────────────────────────────────────
# MAIN – WIDGET PREMIUM
# ─────────────────────────────────────────────
def main():
    global root, canvas, status_label, accent_bar, pulse_canvas

    threading.Thread(target=udp_server, daemon=True).start()

    root = tk.Tk()
    root.title("SparkHub v3.0")
    root.resizable(False, False)
    root.attributes("-topmost", True)
    root.attributes("-alpha", 0.90)
    root.overrideredirect(True)   # sem barra de título nem botões de controle

    # ── Tamanho e posição ──
    WIN_W, WIN_H = 115, 31
    try:
        import ctypes as _ct
        _u = _ct.windll.user32
        pw = _u.GetSystemMetrics(0)
        ph = _u.GetSystemMetrics(1)
    except Exception:
        pw, ph = 1920, 1080

    x = pw - WIN_W - 7
    y = ph - WIN_H - 25
    root.geometry(f"{WIN_W}x{WIN_H}+{x}+{y}")
    print(f"[SYSTRAY] Posição: {x},{y} | Monitor: {pw}x{ph}")

    # ── Cores base ──
    BG   = "#0e0e20"
    BG2  = "#12122a"
    BORD = "#2a2a50"

    # ── Moldura externa (borda) ──
    root.configure(bg=BORD)

    card = tk.Frame(root, bg=BG, bd=0)
    card.pack(fill="both", expand=True, padx=1, pady=1)

    # Accent bar (borda superior colorida)
    accent_bar = tk.Frame(card, bg=COLORS["green"]["accent"], height=2)
    accent_bar.pack(side="top", fill="x")

    # Layout horizontal
    body = tk.Frame(card, bg=BG)
    body.pack(fill="both", expand=True, padx=4, pady=2)

    # ── Canvas Círculo (Ícone) ──
    canvas = tk.Canvas(body, width=21, height=21, bg=BG, highlightthickness=0)
    canvas.pack(side="left", padx=(0, 4))

    # ── Textos ──
    info_frame = tk.Frame(body, bg=BG)
    info_frame.pack(side="left", fill="both", expand=True)

    title_frame = tk.Frame(info_frame, bg=BG)
    title_frame.pack(anchor="w")

    tk.Label(title_frame, text="SPARKHUB",
             font=("Segoe UI", 6, "bold"),
             fg="#818cf8", bg=BG).pack(side="left")

    tk.Label(title_frame, text=" v3.0",
             font=("Segoe UI", 5),
             fg="#475569", bg=BG).pack(side="left")

    status_label = tk.Label(info_frame, text=COLORS["green"]["text"],
                            font=("Segoe UI", 7, "bold"),
                            fg=COLORS["green"]["hi"], bg=BG)
    status_label.pack(anchor="w")

    # ── Dot de Pulso (direita) ──
    pulse_frame = tk.Frame(body, bg=BG)
    pulse_frame.pack(side="right", padx=(2, 0))

    pulse_canvas = tk.Canvas(pulse_frame, width=8, height=8, bg=BG, highlightthickness=0)
    pulse_canvas.pack()

    # Bindings para interatividade
    for widget in (root, card, body, info_frame, title_frame, status_label, canvas, pulse_canvas):
        widget.bind("<Button-3>", show_menu)
        widget.bind("<Double-Button-1>", lambda e: open_app("dashboard"))
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)

    draw_circle("green")
    animate_pulse()

    print("[SYSTRAY] ✅ Widget premium ativo!")
    root.mainloop()


if __name__ == "__main__":
    main()
