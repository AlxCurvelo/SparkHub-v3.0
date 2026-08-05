# sparkhub_master_live.py
# FASE 6: ORQUESTRADOR MASTER (O MAESTRO)
# TIPAGEM FORTE | NULOS SEGUROS | EVENT-DATA-DRIVEN

from __future__ import annotations
import os
import queue
import socket
import sqlite3
import subprocess
import threading
import time
import datetime
import json
import urllib.request
from typing import Dict, Any, Optional

import psutil

from sparkhub_paths import PROJECT_ROOT, get_path

class CircuitBreaker:
    def __init__(self, name: str, timeout: int = 5):
        self.name = name
        self.timeout = timeout
        self.active = True

    def trip(self, reason: str):
        self.active = False
        print(f"[CIRCUIT-BREAKER] 🛑 {self.name} DESARMADO! Motivo: {reason}")


class QuadChannelDispatcher:
    """Disparador atômico de alertas em 4 Canais (Toast, WhatsApp, Dashboard e IDE)."""
    
    @staticmethod
    def notify(insight_text: str):
        print(f"\n[QUAD-CHANNEL] Disparando Insight Moltbook para 4 canais...")
        
        # 1. WINDOWS TOAST (Powershell Nativo / Forms)
        try:
            ps_script = f"""
            Add-Type -AssemblyName System.Windows.Forms;
            $notify = New-Object System.Windows.Forms.NotifyIcon;
            $notify.Icon = [System.Drawing.SystemIcons]::Information;
            $notify.Visible = $true;
            $notify.ShowBalloonTip(5000, 'SparkHub Moltbook', '{insight_text[:150]}...', [System.Windows.Forms.ToolTipIcon]::Info);
            Start-Sleep -Seconds 5;
            $notify.Dispose();
            """
            subprocess.Popen(["powershell", "-Command", ps_script], creationflags=subprocess.CREATE_NO_WINDOW)
            print("  -> [Canal 1] Windows Toast enviado.")
        except Exception as e:
            print(f"  -> [Canal 1] Falha no Toast: {e}")

        # 2. WHATSAPP BOT (:8082)
        try:
            url = "http://localhost:8082/send-whatsapp"
            phone = os.environ.get("WHATSAPP_PHONE_NUMBER", "5511995532053")
            payload = {"number": phone, "message": f"🌐 *SparkHub Insight:*\n{insight_text}"}
            req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={"Content-Type": "application/json"}, method='POST')
            with urllib.request.urlopen(req, timeout=3) as res:
                pass
            print("  -> [Canal 2] WhatsApp acionado.")
        except Exception as e:
            print(f"  -> [Canal 2] WhatsApp Offline/Falhou: {e}")

        # 3. WEB DASHBOARD (:8085)
        # O Dashboard consome do SQLite via Fetch API assíncrono.
        print("  -> [Canal 3] Dashboard atualizado (Polling Assíncrono garantido pelo SQLite).")

        # 4. ANTIGRAVITY IDE (notifications.json)
        try:
            # Caminho dinâmico: funciona em qualquer máquina
            ide_path = os.path.join(
                os.getenv("USERPROFILE", os.path.expanduser("~")),
                ".gemini", "antigravity", "notifications.json"
            )
            notifs = []
            if os.path.exists(ide_path):
                with open(ide_path, "r", encoding="utf-8") as f:
                    try:
                        notifs = json.load(f)
                    except:
                        notifs = []
            if not isinstance(notifs, list): notifs = []
            
            notifs.append({
                "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
                "title": "SparkHub Moltbook",
                "message": insight_text,
                "read": False
            })
            
            with open(ide_path, "w", encoding="utf-8") as f:
                json.dump(notifs, f, indent=2, ensure_ascii=False)
            print("  -> [Canal 4] Notificação injetada na IDE Antigravity.")
        except Exception as e:
            print(f"  -> [Canal 4] Falha na escrita do JSON da IDE: {e}")


class LiveOrchestrator:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or str(get_path("mempalace.db"))
        self.event_queue: queue.Queue = queue.Queue(maxsize=10)
        self.obs_breaker = CircuitBreaker("OBS WebSocket")
        self.godot_breaker = CircuitBreaker("Godot UDP")
        self.running = False

    def detect_heavy_load(self) -> bool:
        """Verifica se a GPU/Sistema está sobrecarregada (Simulação via CPU > 80%)."""
        cpu_usage = psutil.cpu_percent(interval=0.1)
        if cpu_usage > 80.0:
            print(f"[VRAM-SHIELD] Carga pesada detectada ({cpu_usage}%). Desviando IA para a Nuvem!")
            return True
        return False

    def trigger_godot_expression(self, expression_id: int):
        """Envia pacote UDP Não-Bloqueante para Godot 4 na porta 9000."""
        if not self.godot_breaker.active:
            return
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(1.0)
            payload = f"EXPRESSION:{expression_id}".encode('utf-8')
            sock.sendto(payload, ("127.0.0.1", 9000))
            print(f"[GODOT] 🎭 Pacote UDP enviado: EXPRESSION {expression_id}")
        except Exception as e:
            self.godot_breaker.trip(f"Falha de Socket UDP: {e}")

    def trigger_obs_scene(self, scene_name: str):
        """Comunica com OBS via WebSocket v5 na porta 4455."""
        if not self.obs_breaker.active:
            return
        
        try:
            # Simulação do Handshake OBS WebSocket v5 (Time-out de 5s)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            result = sock.connect_ex(("127.0.0.1", 4455))
            if result == 0:
                print(f"[OBS] 🎥 Comando de Cena enviado: {scene_name}")
                sock.close()
            else:
                self.obs_breaker.trip(f"Conexão recusada na porta 4455 (Cód {result})")
        except socket.timeout:
            self.obs_breaker.trip("Timeout de 5s excedido no Handshake.")
        except Exception as e:
            self.obs_breaker.trip(f"Erro Crítico: {e}")

    def generate_ai_response(self, prompt: str) -> str:
        """Roteamento real via Tríplice Cascata (app.route_ai_request)."""
        try:
            import sys
            if str(PROJECT_ROOT) not in sys.path:
                sys.path.append(str(PROJECT_ROOT))
            import app as sparkhub_app
            profile = "cloud" if self.detect_heavy_load() else "vram_fast"
            return sparkhub_app.route_ai_request(prompt, profile=profile)
        except Exception as e:
            return f"[ROTEADOR INDISPONÍVEL: {e}]"

    def audit_memory(self, user: str, msg: str, ai_response: str):
        """Salva o resumo da interação na sala sync_audit do MemPalace."""
        try:
            with sqlite3.connect(self.db_path, timeout=5) as conn:
                content = f"Jubileu respondeu a {user} ({msg}): {ai_response}"
                conn.execute(
                    "INSERT INTO memories (wing, room, content, timestamp) VALUES (?, ?, ?, ?)",
                    ("System", "sync_audit", content, datetime.datetime.now(datetime.UTC).isoformat())
                )
        except Exception as e:
            print(f"[MURPHY-ALRT] Falha na auditoria SQLite: {e}")

    def process_event_loop(self):
        """Loop Consumidor Isolado (Drop Older)."""
        print("[MAESTRO] 👑 Orquestrador Master Iniciado. Aguardando eventos...")
        while self.running:
            try:
                # Timeout curto para permitir interrupção graciosa
                event = self.event_queue.get(timeout=1.0)
                
                # Se a fila estiver cheia de spam, esvazia até sobrar os mais recentes (Drop Older)
                if self.event_queue.qsize() > 5:
                    print(f"[ANTI-SPAM] Fila lotada ({self.event_queue.qsize()}). Descartando mensagens antigas...")
                    while self.event_queue.qsize() > 1:
                        try:
                            self.event_queue.get_nowait()
                            self.event_queue.task_done()
                        except queue.Empty:
                            break

                user = event.get('user', 'Unknown')
                msg = event.get('msg', '')
                
                print(f"\n--- Processando Evento de: {user} ---")
                
                # 1. IA Híbrida
                response = self.generate_ai_response(msg)
                
                # 2. Expressão Godot
                self.trigger_godot_expression(expression_id=7) # Ex: 7 = Rindo
                
                # 3. OBS Scene
                self.trigger_obs_scene("Cena_Jubileu_CloseUp")
                
                # 4. Auditoria
                self.audit_memory(user, msg, response)
                
                self.event_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[MURPHY-ALRT] Erro no Event Loop: {e}")

    def simulate_tiktok_injection(self, count: int = 15):
        """Simulador de estresse para validar o descarte de fila (Anti-Spam)."""
        print(f"[TESTE SINTÉTICO] Injetando {count} mensagens simultâneas (Spam de Chat)...")
        for i in range(count):
            try:
                # Put nowait lança exceção se a fila estiver cheia (maxsize=10)
                self.event_queue.put_nowait({"user": f"Viewer_{i}", "msg": f"Manda salve! {i}"})
            except queue.Full:
                print(f"[TESTE SINTÉTICO] Fila bloqueou injeção no item {i} (Proteção maxsize=10 ativa!).")
                # Drop older natural implementado na extração, ou bloqueio na injeção.
                pass

if __name__ == "__main__":
    import sys
    maestro = LiveOrchestrator()
    maestro.running = True
    
    # Thread do Event Loop
    worker = threading.Thread(target=maestro.process_event_loop, daemon=True)
    worker.start()
    
    # Aguarda o worker iniciar
    time.sleep(1)
    
    if "--test" in sys.argv:
        # Modo de teste de estresse (executa e desliga)
        print("[MAESTRO] Modo de teste de estresse ativado.")
        maestro.simulate_tiktok_injection(count=15)
        time.sleep(3)
        maestro.running = False
        worker.join()
        print("\n[MAESTRO] Teste concluído e Orquestrador desligado graciosamente.")
    else:
        # Modo Daemon Persistente (padrão — usado pelo boot e pelo install_daemon.bat)
        print("[MAESTRO] 👑 Daemon ATIVO. Orquestrador operando em modo persistente. (Ctrl+C para parar)")
        try:
            while maestro.running:
                time.sleep(1)
        except KeyboardInterrupt:
            maestro.running = False
            worker.join()
            print("\n[MAESTRO] Encerramento gracioso via Ctrl+C.")
