"""
SparkHub v3.0 - Pilar 4: Win32 API & Tailscale Antifrágil
Localização: sparkhub/win32_antifragile.py
"""

import ctypes
from ctypes import wintypes
import time

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

class Win32Antifragile:
    """Envelopamento de chamadas C++ para Win32 API protegidas contra crashes."""
    
    @staticmethod
    def get_active_window_title() -> str:
        """Pega o título da janela ativa atual com tolerância a falhas."""
        try:
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return "Nenhuma Janela"
            
            length = user32.GetWindowTextLengthW(hwnd)
            if length == 0:
                return "Janela Sem Título"
                
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            return buff.value
        except Exception as e:
            print(f"[WIN32-MURPHY] Erro ao ler janela: {e}")
            return "Erro de Leitura (Win32)"

    @staticmethod
    def check_tailscale_ip() -> str:
        """Verifica o IP da interface Tailscale nativamente."""
        import socket
        try:
            host_name = socket.gethostname()
            # Tenta encontrar o IP 100.x.x.x
            for ip in socket.gethostbyname_ex(host_name)[2]:
                if ip.startswith("100."):
                    return ip
            return "Tailscale Offline"
        except Exception:
            return "Erro na Rede"

    @staticmethod
    def send_ghost_key(window_title: str, key_code: int = 0x20) -> bool:
        """
        Envia uma tecla em background (Fantasma) via PostMessageW.
        Padrão: 0x20 (SPACE). Usado para mutar/desmutar mic no TikTok Live Studio
        sem tirar o foco do jogo atual (Neon Orbit 360).
        """
        try:
            WM_KEYDOWN = 0x0100
            WM_KEYUP = 0x0101
            # Busca a janela ignorando Case
            hwnd = user32.FindWindowW(None, window_title)
            if not hwnd:
                print(f"[WIN32-MURPHY] Janela '{window_title}' não encontrada para injeção.")
                return False
            
            # PostMessage envia a mensagem para a fila e retorna sem bloquear (Antifrágil)
            user32.PostMessageW(hwnd, WM_KEYDOWN, key_code, 0)
            time.sleep(0.05)
            user32.PostMessageW(hwnd, WM_KEYUP, key_code, 0)
            print(f"[WIN32] Tecla {key_code} injetada na janela '{window_title}' como fantasma.")
            return True
        except Exception as e:
            print(f"[WIN32-MURPHY] Falha ao enviar tecla fantasma: {e}")
            return False

if __name__ == "__main__":
    w32 = Win32Antifragile()
    print("[WIN32] Inicializando subsistema nativo protegido...")
    print(f"-> IP Tailscale: {w32.check_tailscale_ip()}")
    print(f"-> Janela Ativa: {w32.get_active_window_title()}")
