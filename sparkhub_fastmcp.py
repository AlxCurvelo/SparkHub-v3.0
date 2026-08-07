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

import json
import math
import sys
try:
    from sparkhub_embed_worker import get_embedding
except ImportError:
    get_embedding = None

def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    dot = sum(a*b for a,b in zip(v1, v2))
    norm1 = math.sqrt(sum(a*a for a in v1))
    norm2 = math.sqrt(sum(b*b for b in v2))
    if norm1 == 0 or norm2 == 0: return 0.0
    return dot / (norm1 * norm2)

@mcp.tool()
def search_mempalace(query: str, limit: int = 5) -> str:
    """
    Busca memórias e contextos no MemPalace do SparkHub usando Busca Híbrida (FTS5 BM25 + Semântica Vetorial).
    Use esta ferramenta para buscar informações sobre a vida do usuário, projetos, regras de sistema e tecnologias.
    
    Args:
        query: A palavra-chave ou termo de busca.
        limit: Número máximo de resultados de cada método.
    """
    if not os.path.exists(DB_PATH):
        return "Erro: Banco de dados mempalace.db não encontrado."
        
    init_fts5_if_needed()
    
    try:
        combined_results = {} # id -> (wing, room, content, score_type)
        
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            
            # 1. Busca Lexical (FTS5 BM25)
            cur.execute("""
                SELECT rowid, wing, room, content 
                FROM memories_fts 
                WHERE memories_fts MATCH ? 
                ORDER BY rank 
                LIMIT ?;
            """, (query, limit))
            
            for rowid, w, r, c in cur.fetchall():
                combined_results[rowid] = (w, r, c, "FTS5/BM25")
                
            # Fallback Lexical (LIKE) se FTS5 falhar
            if not combined_results:
                cur.execute("""
                    SELECT id, wing, room, content 
                    FROM memories 
                    WHERE content LIKE ? 
                    LIMIT ?;
                """, (f"%{query}%", limit))
                for rowid, w, r, c in cur.fetchall():
                    combined_results[rowid] = (w, r, c, "LIKE")

            # 2. Busca Semântica (Vetorial / Cosine)
            if get_embedding:
                q_vec = get_embedding(query)
                if q_vec:
                    cur.execute("SELECT memory_id, embedding FROM memories_embeddings")
                    sem_scores = []
                    for mem_id, emb_str in cur.fetchall():
                        try:
                            emb_vec = json.loads(emb_str)
                            sim = cosine_similarity(q_vec, emb_vec)
                            sem_scores.append((sim, mem_id))
                        except:
                            pass
                    
                    sem_scores.sort(reverse=True, key=lambda x: x[0])
                    top_sem = sem_scores[:limit]
                    
                    for sim, mem_id in top_sem:
                        if sim < 0.3: continue # threshold mínimo de similaridade
                        if mem_id not in combined_results:
                            cur.execute("SELECT wing, room, content FROM memories WHERE id = ?", (mem_id,))
                            row = cur.fetchone()
                            if row:
                                combined_results[mem_id] = (row[0], row[1], row[2], f"Semântica ({sim:.2f})")

            if not combined_results:
                return "Nenhuma memória encontrada para esta busca."
                
            # --- GANCHO: ESPECIALISTA 6 (RERANKER) ---
            try:
                from sparkhub_reranker import rerank_mempalace_results
                # Passa a lista de tuplas (w, r, c, stype) para o juiz final
                final_results = rerank_mempalace_results(query, list(combined_results.values()))
            except ImportError:
                # Fallback se o módulo não estiver disponível
                final_results = list(combined_results.values())[:5]
                
            result_str = f"🧠 Resultados Rerankeados do MemPalace para '{query}':\n"
            for w, r, c, stype in final_results:
                result_str += f"- [{stype}] [{w}/{r}] {c}\n"
                
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
