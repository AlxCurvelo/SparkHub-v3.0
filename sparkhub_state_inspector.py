# sparkhub_state_inspector.py
# TIPAGEM FORTE | NULOS SEGUROS | EVENT-DATA-DRIVEN

from __future__ import annotations
import os
import socket
import psutil
from typing import Dict, Any, List

from sparkhub_paths import PROJECT_ROOT

class SystemStateInspector:
    def __init__(self, root_dir: str | None = None) -> None:
        self.root_dir: str = root_dir if root_dir else str(PROJECT_ROOT)

    def audit_target(self, target_name: str, target_port: int | None = None) -> Dict[str, Any]:
        file_path = os.path.join(self.root_dir, target_name)
        exists = os.path.exists(file_path)
        port_in_use = False

        if target_port is not None:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                port_in_use = s.connect_ex(('127.0.0.1', target_port)) == 0

        print(f"[AUDITORIA] Alvo: {target_name} | Existe: {exists} | Porta {target_port} Ocupada: {port_in_use}")
        return {"exists": exists, "port_in_use": port_in_use}

if __name__ == "__main__":
    # Teste de execução rápida do protocolo (Fail-Fast)
    inspector = SystemStateInspector()
    print("[GOVERNANÇA] Inicializando Protocolo de Auditoria Prévia de Estado...")
    inspector.audit_target("mempalace.db")
    inspector.audit_target("sparkhub_fastmcp.py")
