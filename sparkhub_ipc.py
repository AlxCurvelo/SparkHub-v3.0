"""
SparkHub v3.0 - Centralized IPC & Signal Manager (sparkhub_ipc.py)
Dispatches UDP signals (Processing, Operational, Error, Action) to the Systray Widget (Port 8087)
and manages inter-process communications securely.
"""

import socket
import json
import os
import datetime

SYSTRAY_PORT = 8087
SYSTRAY_HOST = "127.0.0.1"

def send_systray_signal(state_or_cmd: str, details: str = "") -> bool:
    """
    Sends a UDP packet to the Systray Widget on 127.0.0.1:8087.
    Supported states: 'yellow', 'green', 'red', 'blue', 'open_notepad', 'open_vscode', etc.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.5)
        payload = {
            "cmd": state_or_cmd,
            "details": details,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        # Send raw string or JSON payload
        msg_bytes = json.dumps(payload).encode("utf-8")
        sock.sendto(msg_bytes, (SYSTRAY_HOST, SYSTRAY_PORT))
        # Also send direct state string for compatibility
        sock.sendto(state_or_cmd.encode("utf-8"), (SYSTRAY_HOST, SYSTRAY_PORT))
        sock.close()
        return True
    except Exception as e:
        print(f"[IPC WARN] Could not deliver UDP signal '{state_or_cmd}': {e}")
        return False

def notify_ide_quadchannel(title: str, message: str) -> bool:
    """
    Appends notification to Antigravity IDE notifications.json atomically.
    (Quad-Channel Rule #4).
    """
    try:
        user_profile = os.getenv("USERPROFILE", os.path.expanduser("~"))
        ide_path = os.path.join(user_profile, ".gemini", "antigravity", "notifications.json")
        
        notifs = []
        if os.path.exists(ide_path):
            try:
                with open(ide_path, "r", encoding="utf-8") as f:
                    notifs = json.load(f)
            except Exception:
                notifs = []
                
        if not isinstance(notifs, list):
            notifs = []
            
        notifs.append({
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "title": title,
            "message": message,
            "read": False
        })
        
        # Write atomically
        temp_path = ide_path + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(notifs, f, indent=2, ensure_ascii=False)
        os.replace(temp_path, ide_path)
        return True
    except Exception as e:
        print(f"[IPC WARN] Error writing to IDE Quad-Channel: {e}")
        return False

if __name__ == "__main__":
    print("[IPC ENGINE] Testing UDP broadcast to Systray Widget...")
    success = send_systray_signal("green", "IPC self-test complete.")
    print(f"[IPC ENGINE] Broadcast result: {'SUCCESS' if success else 'FAILED'}")
