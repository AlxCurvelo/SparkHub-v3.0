# sparkhub_fastmcp.py
# TIPAGEM FORTE | NULOS SEGUROS | EVENT-DATA-DRIVEN
"""
SparkHub v3.0 - Pilar 1: FastMCP & SQLite RAG
Protocolo MCP (Model Context Protocol)
"""

from __future__ import annotations
import os
import sqlite3
from typing import Any, Dict, List

from fastmcp import FastMCP

from sparkhub_paths import get_path

# Instância do Servidor FastMCP
mcp = FastMCP("SparkHub-Brain")
DB_PATH = str(get_path("mempalace.db"))

# Centralized FTS initialization imported from sparkhub_db
from sparkhub_db import init_fts5_if_needed

@mcp.tool()
def search_mempalace(query: str, limit: int = 5) -> str:
    """
    Busca memórias e contextos no MemPalace do SparkHub usando FTS5 (BM25).
    Use esta ferramenta para buscar informações sobre a vida do usuário, projetos (como Jubileu), regras de sistema e tecnologias.
    
    Args:
        query: A palavra-chave ou termo de busca.
        limit: Número máximo de resultados.
    """
    if not os.path.exists(DB_PATH):
        return "Erro: Banco de dados mempalace.db não encontrado."
        
    init_fts5_if_needed()
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            # Busca usando o índice FTS5
            cur.execute("""
                SELECT wing, room, content 
                FROM memories_fts 
                WHERE memories_fts MATCH ? 
                ORDER BY rank 
                LIMIT ?;
            """, (query, limit))
            
            rows = cur.fetchall()
            
            if not rows:
                # Fallback para LIKE se a query FTS falhar por sintaxe estrita
                cur.execute("""
                    SELECT wing, room, content 
                    FROM memories 
                    WHERE content LIKE ? 
                    LIMIT ?;
                """, (f"%{query}%", limit))
                rows = cur.fetchall()

            if not rows:
                return "Nenhuma memória encontrada para esta busca."
                
            result_str = f"🧠 Resultados do MemPalace para '{query}':\n"
            for w, r, c in rows:
                result_str += f"- [{w}/{r}] {c}\n"
                
            return result_str
            
    except Exception as e:
        return f"Erro de banco de dados: {str(e)}"

@mcp.tool()
def read_all_wings() -> str:
    """
    Retorna a lista de todas as categorias (Wings e Rooms) disponíveis no MemPalace.
    Útil para entender a estrutura de memória do SparkHub.
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT wing, room FROM memories ORDER BY wing, room;")
            rows = cur.fetchall()
            if not rows:
                return "MemPalace está vazio."
                
            result_str = "🏰 Estrutura do MemPalace:\n"
            for w, r in rows:
                result_str += f"- Ala: {w} | Sala: {r}\n"
            return result_str
    except Exception as e:
        return f"Erro de banco de dados: {str(e)}"

if __name__ == "__main__":
    # Sincroniza o índice de busca rápida silenciosamente
    init_fts5_if_needed()
    # Inicia o servidor via Stdio (Padrão MCP para Cursor/Claude)
    mcp.run()
