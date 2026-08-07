
import os
from dotenv import load_dotenv
load_dotenv(r"D:\SparkHub\.env")

import json
import logging
import requests
import concurrent.futures
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Fallback keywords
PALAVRAS_CHAVE_BUSCA = [
    "projeto", "e-mail", "email", "documento", "arquivo", "drive",
    "contrato", "orcamento", "orçamento", "prazo", "relatorio", "relatório", "dados",
    "inconclusos", "pendentes", "iniciado"
]

class SearchClassification(BaseModel):
    precisa_buscar: bool
    raciocinio: str
    queries: list[str]
    fontes: list[str]

class SearchAgent:
    """
    Agente local de busca desacoplada.
    Usa Ollama (modelo leve) para classificar intenção e gerar queries.
    Executa buscas em paralelo no MemPalace, Gmail e Drive via Orchestrator (MCP).
    Retorna bloco de contexto formatado para injeção no prompt.
    """
    
    def __init__(self, modelo_local: str = None):
        self.modelo = modelo_local or os.environ.get("SEARCH_AGENT_MODEL", "qwen2.5:7b")
        self.timeout = int(os.environ.get("SEARCH_AGENT_TIMEOUT", 10))
        self.api_token = os.environ.get("SPARKHUB_API_TOKEN", "")
        
    def _classificar_offline(self, prompt: str) -> SearchClassification:
        precisa = any(p in prompt.lower() for p in PALAVRAS_CHAVE_BUSCA)
        return SearchClassification(
            precisa_buscar=precisa,
            raciocinio="Fallback heurístico offline",
            queries=[prompt],
            fontes=["mempalace", "gmail", "drive"] if precisa else []
        )
        
    def classificar(self, prompt: str) -> SearchClassification:
        try:
            payload = {
                "model": self.modelo,
                "prompt": f"Analise o seguinte prompt e decida se ele requer busca em bases de conhecimento locais ou em nuvem (email, drive, projetos antigos). Retorne APENAS um JSON válido seguindo este formato rigoroso: {{\"precisa_buscar\": true/false, \"raciocinio\": \"sua justificativa\", \"queries\": [\"palavras-chave 1\", \"palavras-chave 2\"], \"fontes\": [\"mempalace\", \"gmail\", \"drive\"]}}. Use no máximo 2 queries curtas de poucas palavras cada, baseadas na necessidade de busca do usuário. Prompt: '{prompt}'",
                "stream": False,
                "format": "json"
            }
            res = requests.post("http://127.0.0.1:11434/api/generate", json=payload, timeout=5)
            res.raise_for_status()
            data = res.json()["response"]
            parsed = json.loads(data)
            return SearchClassification(**parsed)
        except Exception as e:
            logger.warning(f"[SEARCH AGENT] Falha ao usar {self.modelo} para classificação. Usando fallback offline. Erro: {e}")
            return self._classificar_offline(prompt)

    def _call_mcp_tool(self, tool_name: str, arguments: dict):
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "jsonrpc": "2.0",
            "id": "search_agent",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        try:
            res = requests.post("http://127.0.0.1:8000/", json=payload, headers=headers, timeout=5)
            res.raise_for_status()
            data = res.json()
            if "result" in data:
                return data["result"]
            if "error" in data:
                logger.error(f"[SEARCH AGENT] Erro na tool {tool_name}: {data['error']}")
            return None
        except Exception as e:
            logger.error(f"[SEARCH AGENT] Erro na chamada HTTP para {tool_name}: {e}")
            return None

    def executar_buscas(self, queries: list[str], fontes: list[str]) -> dict:
        resultados = {"mempalace": [], "gmail": [], "drive": []}
        
        # Imports locais só para MemPalace, pois Gmail/Drive passam pela 8000
        from sparkhub_db import mempalace_search
        
        def _buscar_mempalace(query):
            try:
                res = mempalace_search(query)
                if res and "Nenhum resultado" not in res:
                    resultados["mempalace"].append(res)
            except Exception as e:
                logger.error(f"[SEARCH AGENT] Erro no MemPalace: {e}")
                
        def _buscar_gmail(query):
            res = self._call_mcp_tool("search_gmail", {"query": query})
            if res:
                resultados["gmail"].append(str(res))
                
        def _buscar_drive(query):
            res = self._call_mcp_tool("search_drive_docs", {"query": query})
            if res:
                resultados["drive"].append(str(res))

        # Execute searches in parallel
        futures = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            for q in queries:
                if "mempalace" in fontes:
                    futures.append(executor.submit(_buscar_mempalace, q))
                if "gmail" in fontes:
                    futures.append(executor.submit(_buscar_gmail, q))
                if "drive" in fontes:
                    futures.append(executor.submit(_buscar_drive, q))
            
            # Wait for all with timeout
            concurrent.futures.wait(futures, timeout=self.timeout)
            
        return resultados

    def formatar_contexto(self, resultados: dict) -> str:
        ctx_parts = []
        for fonte, itens in resultados.items():
            if itens:
                ctx_parts.append(f"[{fonte.upper()}]")
                for item in itens:
                    ctx_parts.append(str(item)[:500].strip())
        
        if ctx_parts:
            return "=== CONTEXTO PRÉ-BUSCADO (PESQUISA DESACOPLADA) ===\n" + "\n".join(ctx_parts) + "\n=======================================================\n"
        return ""
