# sparkhub_obs_tailscale.py
# TIPAGEM FORTE | NULOS SEGUROS | EVENT-DATA-DRIVEN

from __future__ import annotations
import obsws_python as obs
from typing import Optional, Dict, Any
import socket

class OBSBridgeManager:
    def __init__(self, host: str = "127.0.0.1", port: int = 4455, password: str = "") -> None:
        self.host: str = host
        self.port: int = port
        self.password: str = password

    def send_command(self, request_type: str, data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        try:
            # Tenta conectar no OBS via WebSocket Oficial
            client = obs.ReqClient(host=self.host, port=self.port, password=self.password, timeout=1.5)
            if data is None:
                response = client.send(request_type)
            else:
                response = client.send(request_type, data)
            client.disconnect()
            return vars(response) if response else {}
        except Exception as e:
            print(f"[MURPHY-ALRT] Conexão com OBS falhou: {e}")
            return None

# Instanciação do Gerenciador OBS
obs_manager = OBSBridgeManager()

if __name__ == "__main__":
    print("[TESTE] Inicializando Ponte OBS WebSocket (v5)...")
    res = obs_manager.send_command("GetVersion")
    if res:
        print(f"[SUCESSO] Resposta do OBS: {res}")
    else:
        print("[BYPASS] OBS inativo ou indisponível. Fluxo segue normal.")
