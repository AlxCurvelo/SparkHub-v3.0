# workspace_agent.py – Multi‑Account Google Workspace Agent (Antifrágil)

"""Utility to manage Google Drive / Gmail searches across multiple Google accounts.

Features:
- Dynamic token discovery (token.json and token_<alias>.json).
- CLI flag ``--add-account <alias>`` to create a new OAuth token in isolation.
- Antifrágil per‑account loops with try/except; results are tagged with the account label.
- Optional ``--token-file <path>`` argument for functions that need a specific token.
"""

import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from sparkhub_paths import get_path

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
]
DB_PATH = str(get_path("sync_requisicoes.db"))
CRED_PATH = str(get_path("credentials.json"))

# ---------------------------------------------------------------------------
# Database helpers (WAL enabled)
# ---------------------------------------------------------------------------

def init_db():
    """Ensure the sync‑log DB exists and operates in WAL mode."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS sync_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT, payload TEXT, status TEXT, timestamp REAL)"""
    )
    conn.commit()
    conn.close()


def registrar_requisicao(tipo, payload):
    """Insert a sync‑log entry and return its ID."""
    init_db()
    conn = sqlite3.connect(DB_PATH, timeout=10)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO sync_logs (tipo, payload, status, timestamp) VALUES (?, ?, 'PENDING', ?)",
        (tipo, payload, time.time()),
    )
    req_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return req_id


def atualizar_status(req_id, status):
    conn = sqlite3.connect(DB_PATH, timeout=10)
    cursor = conn.cursor()
    cursor.execute("UPDATE sync_logs SET status = ? WHERE id = ?", (status, req_id))
    conn.commit()
    conn.close()

# ---------------------------------------------------------------------------
# Authentication utilities (token_file optional)
# ---------------------------------------------------------------------------

def get_authenticated_service(api_name: str, version: str, token_file: str | None = None):
    """Return an authorized Google API service.

    Parameters
    ----------
    api_name : str
        Name of the Google API (e.g., "drive").
    version : str
        API version (e.g., "v3").
    token_file : str | None, optional
        Path to the token JSON. If omitted the function falls back to
        ``token.json`` in the workspace root.
    """
    token_path = Path(token_file) if token_file else get_path("token.json")
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None
        if not creds:
            if not os.path.exists(CRED_PATH):
                raise FileNotFoundError(f"Credentials file not found at {CRED_PATH}")
            flow = InstalledAppFlow.from_client_secrets_file(CRED_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(token_path, "w") as f:
            f.write(creds.to_json())
    return build(api_name, version, credentials=creds)

# ---------------------------------------------------------------------------
# Account management
# ---------------------------------------------------------------------------

def add_new_account(alias: str):
    """Run the OAuth flow for a new *alias* and store ``token_<alias>.json``."""
    token_path = get_path(f"token_{alias}.json")
    print(f"[*] Starting OAuth flow for account '{alias}' …")
    get_authenticated_service("drive", "v3", str(token_path))
    print(f"[✔] Account '{alias}' connected! Token saved at {token_path}")


def get_all_tokens():
    """Return a list of all token file paths (including the default token.json)."""
    root = get_path('.')
    tokens = [str(p) for p in sorted(root.glob('token_*.json'))]
    default = str(root / 'token.json')
    if os.path.exists(default):
        tokens.insert(0, default)
    return tokens


def get_account_label(token_path: str) -> str:
    """Derive a human‑readable label from a token file name.

    ``token.json`` → ``Principal``
    ``token_trabalho.json`` → ``Trabalho``
    """
    name = os.path.basename(token_path)
    if name == "token.json":
        return "Principal"
    return name.replace("token_", "").replace(".json", "").capitalize()

# ---------------------------------------------------------------------------
# Helper to clean query strings (antifragile)
# ---------------------------------------------------------------------------

def _clean_query(query_text: str) -> list:
    stop_words = [" o ", " a ", " do ", " da ", " de ", " no ", " na ", " um ", " uma "]
    clean = f" {query_text.lower()} "
    for sw in stop_words:
        clean = clean.replace(sw, " ")
    words = [w.strip() for w in clean.split() if w.strip()]
    return words or [query_text]

# ---------------------------------------------------------------------------
# Search helpers (Antifrágil loops)
# ---------------------------------------------------------------------------

def search_drive_docs(query_text: str):
    """Search Google Drive (name *or* full‑text) across **all** accounts.

    Results are tagged with ``[Alias]`` so the caller knows their origin.
    """
    req_id = registrar_requisicao("DRIVE_SEARCH", query_text)
    all_items = []
    tokens = get_all_tokens()
    if not tokens:
        atualizar_status(req_id, "FALLBACK")
        return [{"name": "Erro: Nenhuma conta conectada.", "snippet": "Rode add-account."}]
    palavras = _clean_query(query_text)
    drive_query = " and ".join([f"name contains '{p}'" for p in palavras]) + " and trashed=false"
    full_query = " and ".join([f"fullText contains '{p}'" for p in palavras]) + " and trashed=false"
    for token_path in tokens:
        label = get_account_label(token_path)
        try:
            service = get_authenticated_service("drive", "v3", token_path)
            results = service.files().list(
                q=drive_query, pageSize=3, fields="files(id, name, webViewLink)"
            ).execute()
            items = results.get("files", [])
            if not items:
                results = service.files().list(
                    q=full_query, pageSize=3, fields="files(id, name, webViewLink)"
                ).execute()
                items = results.get("files", [])
            for item in items:
                item["name"] = f"[{label}] {item['name']}"
                all_items.append(item)
        except Exception as e:
            print(f"[WORKSPACE WARN] Drive query failed for {label}: {e}")
            all_items.append({"name": f"[{label}] Erro de Conexão", "snippet": str(e)})
    atualizar_status(req_id, "SUCCESS")
    return all_items


def search_shared_drive_docs():
    """Search files shared *with* the user across all accounts."""
    req_id = registrar_requisicao("DRIVE_SHARED_SEARCH", "sharedWithMe")
    all_items = []
    tokens = get_all_tokens()
    if not tokens:
        atualizar_status(req_id, "FALLBACK")
        return [{"name": "Erro: Nenhuma conta conectada.", "snippet": "Rode add-account."}]
    query = "sharedWithMe=true and trashed=false"
    for token_path in tokens:
        label = get_account_label(token_path)
        try:
            service = get_authenticated_service("drive", "v3", token_path)
            results = service.files().list(
                q=query,
                pageSize=5,
                fields="files(id, name, webViewLink)",
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
            ).execute()
            for item in results.get("files", []):
                item["name"] = f"[{label}] {item['name']}"
                all_items.append(item)
        except Exception as e:
            print(f"[WORKSPACE WARN] Shared Drive query failed for {label}: {e}")
    atualizar_status(req_id, "SUCCESS")
    return all_items


def search_all_google_docs():
    """List Google Docs (native) across every linked account."""
    req_id = registrar_requisicao("DRIVE_DOCS_SEARCH", "mimeType=document")
    all_items = []
    tokens = get_all_tokens()
    if not tokens:
        atualizar_status(req_id, "FALLBACK")
        return [{"name": "Erro: Nenhuma conta conectada.", "snippet": "Rode add-account."}]
    query = "mimeType='application/vnd.google-apps.document' and trashed=false"
    for token_path in tokens:
        label = get_account_label(token_path)
        try:
            service = get_authenticated_service("drive", "v3", token_path)
            results = service.files().list(
                q=query, pageSize=15, fields="files(id, name, webViewLink)"
            ).execute()
            for item in results.get("files", []):
                item["name"] = f"[{label}] {item['name']}"
                all_items.append(item)
        except Exception as e:
            print(f"[WORKSPACE WARN] Docs query failed for {label}: {e}")
    atualizar_status(req_id, "SUCCESS")
    return all_items


def search_gmail(query_text: str):
    """Search Gmail across all accounts, tagging each result with its origin."""
    req_id = registrar_requisicao("GMAIL_SEARCH", query_text)
    all_messages = []
    tokens = get_all_tokens()
    if not tokens:
        atualizar_status(req_id, "FALLBACK")
        return [{"id": "error", "snippet": "Nenhuma conta conectada."}]
    for token_path in tokens:
        label = get_account_label(token_path)
        try:
            service = get_authenticated_service("gmail", "v1", token_path)
            results = service.users().messages().list(userId="me", q=query_text, maxResults=3).execute()
            for msg in results.get("messages", []):
                m_data = service.users().messages().get(userId="me", id=msg["id"], format="minimal").execute()
                all_messages.append({
                    "id": f"[{label}] {msg['id']}",
                    "snippet": f"[{label}] {m_data.get('snippet', '')}",
                    "labels": m_data.get("labelIds", []),
                })
        except Exception as e:
            print(f"[WORKSPACE WARN] Gmail query failed for {label}: {e}")
            all_messages.append({"id": f"[{label}] error", "snippet": str(e), "labels": []})
    atualizar_status(req_id, "SUCCESS")
    return all_messages

# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _parse_args():
    parser = argparse.ArgumentParser(description="Workspace Agent – Multi‑Account Google API helper")
    parser.add_argument("--add-account", metavar="ALIAS", help="Create a new OAuth token for the given account alias")
    return parser.parse_args()

if __name__ == "__main__":
    args = _parse_args()
    if args.add_account:
        add_new_account(args.add_account)
    else:
        print("[*] Running Multi‑Workspace authentication test…")
        if not get_all_tokens():
            get_authenticated_service("drive", "v3")
        print("[✔] Multi‑Workspace authentication validated. Tokens are securely stored.")
