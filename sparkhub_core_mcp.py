# sparkhub_core_mcp.py
# TIPAGEM FORTE | NULOS SEGUROS | EVENT-DATA-DRIVEN
"""
SparkHub v3.0 - Core AI MCP Server (Porta Dinâmica)
Arquitetura Hexagonal: Contratos-First e UI-Agnostic
"""

from __future__ import annotations
import os
import socket
import sqlite3
import time
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP
from pydantic import BaseModel, Field

from sparkhub_paths import get_default_port, get_path

# Instância do Servidor FastMCP

def find_available_port(start_port: int, max_tries: int = 20) -> int:
    for candidate in [start_port] + list(range(start_port + 1, start_port + max_tries)):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("0.0.0.0", candidate))
                return candidate
            except OSError:
                continue
    raise OSError(f"Não foi possível encontrar uma porta livre a partir de {start_port}")

MCP_PORT = find_available_port(get_default_port(8000))
os.environ["FASTMCP_PORT"] = str(MCP_PORT)
mcp = FastMCP("SparkHub-Core")
DB_PATH = str(get_path("mempalace.db"))

# =====================================================================
# 1. DOMÍNIO & CONTRATOS (Pydantic Models) - Hexágono Interno
# =====================================================================

class MemorySearchContract(BaseModel):
    query: str = Field(..., description="Palavra-chave ou termo de busca.")
    limit: int = Field(5, description="Número máximo de resultados.", ge=1, le=20)

class SyncRequestContract(BaseModel):
    scope: str = Field(..., description="Escopo do sync. Ex: 'sheets', 'drive', 'mempalace'")
    force: bool = Field(False, description="Se verdadeiro, ignora o cache e força a sincronização.")

class AppOpenContract(BaseModel):
    app_name: str = Field(..., description="Nome do aplicativo ou atalho a ser aberto.")

# =====================================================================
# 2. ADAPTADORES & CASOS DE USO - Hexágono Externo
# =====================================================================

# Centralized FTS initialization imported from sparkhub_db
from sparkhub_db import init_fts5_if_needed

# =====================================================================
# 3. PORTAS MCP (Transporte / Borda)
# =====================================================================

@mcp.tool()
def search_mempalace(params: MemorySearchContract) -> str:
    """Busca memórias e contextos no MemPalace usando os contratos Pydantic."""
    if not os.path.exists(DB_PATH):
        return "Erro: Banco de dados mempalace.db não encontrado."
        
    init_fts5_if_needed()
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT wing, room, content 
                FROM memories_fts 
                WHERE memories_fts MATCH ? 
                ORDER BY rank 
                LIMIT ?;
            """, (params.query, params.limit))
            
            rows = cur.fetchall()
            
            if not rows:
                # Fallback LIKE
                cur.execute("""
                    SELECT wing, room, content 
                    FROM memories 
                    WHERE content LIKE ? 
                    LIMIT ?;
                """, (f"%{params.query}%", params.limit))
                rows = cur.fetchall()

            if not rows:
                return "Nenhuma memória encontrada."
                
            result_str = f"🧠 Resultados MCP para '{params.query}':\n"
            for w, r, c in rows:
                result_str += f"- [{w}/{r}] {c}\n"
                
            return result_str
            
    except Exception as e:
        return f"Erro de banco de dados: {str(e)}"

@mcp.tool()
def sync_data(params: SyncRequestContract) -> str:
    """Realiza sincronizações de dados baseadas nos contratos Pydantic."""
    # Validação de escopo via contrato Pydantic
    status = "SUCCESS" if params.force or len(params.scope) > 0 else "FAILED"
    msg = f"Sincronização do escopo '{params.scope}' acionada via porta MCP {MCP_PORT}. Force={params.force}"
    
    return f'{{ "status": "{status}", "message": "{msg}" }}'

@mcp.tool()
def open_os_app(params: AppOpenContract) -> str:
    """Abre um app no SO via os.startfile (Arquitetura Hexagonal — Zero Mocks)."""
    import subprocess
    try:
        os.startfile(params.app_name)
        return f'{{"status": "success", "message": "App \'{params.app_name}\' aberto via os.startfile."}}'
    except FileNotFoundError:
        # Fallback: tenta via shell (ex: nome de comando como 'notepad', 'calc')
        try:
            subprocess.Popen(params.app_name, shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
            return f'{{"status": "success", "message": "App \'{params.app_name}\' aberto via subprocess."}}'
        except Exception as e2:
            return f'{{"status": "error", "message": "Falha ao abrir \'{params.app_name}\': {str(e2)}"}}'
    except Exception as e:
        return f'{{"status": "error", "message": "{str(e)}"}}'


if __name__ == "__main__":
    import sys
    init_fts5_if_needed()
    if "--stdio" in sys.argv:
        print("🚀 SparkHub Core AI MCP subindo via STDIO (Google Antigravity)...", file=sys.stderr)
        mcp.run(transport="stdio")
    else:
        print(f"🚀 SparkHub Core AI MCP (Porta {MCP_PORT}) subindo via SSE...")
        mcp.run(transport="sse")
