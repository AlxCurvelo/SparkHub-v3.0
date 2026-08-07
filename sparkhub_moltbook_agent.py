import os
import time
import json
import logging
import threading
import requests
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class DataSourceNotAvailable(Exception):
    pass

class DataSource(ABC):
    @abstractmethod
    def listar_skills(self, submolt: str) -> List[Dict]:
        """Retorna lista de skills disponíveis no submolt."""
        pass
    
    @abstractmethod
    def ler_skill(self, skill_id: str) -> str:
        """Retorna o conteúdo completo de um skill."""
        pass

class LocalDirectorySource(DataSource):
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir, exist_ok=True)
            
    def listar_skills(self, submolt: str) -> List[Dict]:
        target_dir = os.path.join(self.base_dir, submolt)
        if not os.path.exists(target_dir):
            return []
            
        skills = []
        for filename in os.listdir(target_dir):
            if filename.endswith(".md") and filename != "README.md":
                skills.append({
                    "id": os.path.join(submolt, filename),
                    "titulo": filename.replace(".md", "").replace("_", " ").title(),
                    "autor": "Local Dev"
                })
        return skills
    
    def ler_skill(self, skill_id: str) -> str:
        full_path = os.path.join(self.base_dir, skill_id.replace("/", os.sep))
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

class HTTPEndpointSource(DataSource):
    def __init__(self, endpoint: str, token: str):
        self.endpoint = endpoint
        self.token = token
        self._ativo = bool(endpoint and endpoint != "https://api.moltbook.io")
    
    def listar_skills(self, submolt: str) -> List[Dict]:
        if not self._ativo:
            raise DataSourceNotAvailable("HTTPEndpointSource não configurado. Defina MOLTBOOK_API_ENDPOINT no .env.")
        
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        resp = requests.get(f"{self.endpoint}/submolts/{submolt}/skills", headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json().get("skills", [])
    
    def ler_skill(self, skill_id: str) -> str:
        if not self._ativo:
            raise DataSourceNotAvailable("HTTPEndpointSource não configurado. Defina MOLTBOOK_API_ENDPOINT no .env.")
            
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        resp = requests.get(f"{self.endpoint}/skills/{skill_id}/content", headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.text

class MiniCircuitBreaker:
    def __init__(self, max_falhas=3, timeout=3600):
        self.max_falhas = max_falhas
        self.timeout = timeout
        self.falhas = 0
        self.aberto_ate = 0
    
    def pode_executar(self) -> bool:
        if self.falhas >= self.max_falhas:
            if time.time() < self.aberto_ate:
                return False
            else:
                self.falhas = 0  # Reset após timeout
        return True
    
    def registrar_falha(self):
        self.falhas += 1
        if self.falhas >= self.max_falhas:
            self.aberto_ate = time.time() + self.timeout
            logger.warning(f"[MOLTBOOK CIRCUIT BREAKER] Aberto. Pausando por {self.timeout}s.")
    
    def registrar_sucesso(self):
        if self.falhas > 0:
            logger.info("[MOLTBOOK CIRCUIT BREAKER] Fechado/Recuperado.")
        self.falhas = 0

class MoltbookAgent:
    def __init__(self):
        load_dotenv(r"D:\SparkHub\.env")
        self.enabled = os.environ.get("MOLTBOOK_ENABLED", "false").lower() == "true"
        self.source_type = os.environ.get("MOLTBOOK_SOURCE", "local")
        self.skills_dir = os.environ.get("MOLTBOOK_SKILLS_DIR", r"D:\SparkHub\moltbook_skills")
        self.api_endpoint = os.environ.get("MOLTBOOK_API_ENDPOINT", "")
        self.api_token = os.environ.get("SPARKHUB_API_TOKEN", "") # Use orchestrator token or similar for now
        
        self.default_submolts = [s.strip() for s in os.environ.get("MOLTBOOK_DEFAULT_SUBMOLTS", "godot,python,automacao").split(",")]
        
        if self.source_type == "http":
            self.source = HTTPEndpointSource(self.api_endpoint, self.api_token)
        else:
            self.source = LocalDirectorySource(self.skills_dir)
            
        self.circuit_breaker = MiniCircuitBreaker()
        self._ocioso_thread = None
        self._running = False
        self._idle_consecutive_minutes = 0

    def _ingerir_skill(self, submolt: str, skill: dict) -> bool:
        try:
            conteudo = self.source.ler_skill(skill["id"])
            if not conteudo:
                return False
                
            payload = {
                "jsonrpc": "2.0",
                "id": "moltbook_agent",
                "method": "tools/call",
                "params": {
                    "name": "mempalace_save",
                    "arguments": {
                        "wing": "Moltbook",
                        "room": submolt,
                        "content": f"SKILL: {skill.get('titulo', '')}\\nORIGEM: Moltbook/{submolt}\\nAUTOR: {skill.get('autor', 'IA Anônima')}\\n\\n{conteudo}"
                    }
                }
            }
            
            response = requests.post(
                "http://127.0.0.1:8000/",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_token}"},
                timeout=30
            )
            
            if response.status_code == 200:
                resp_json = response.json()
                if "error" in resp_json:
                    logger.error(f"[MOLTBOOK] Falha ao injetar via Orchestrator: {resp_json['error']}")
                    return False
                logger.info(f"[MOLTBOOK] Skill indexado/verificado: {skill.get('titulo', '')}")
                return True
            else:
                logger.error(f"[MOLTBOOK] Orchestrator recusou ({response.status_code}): {response.text}")
                return False
        except Exception as e:
            logger.error(f"[MOLTBOOK] Falha na ingestao do skill {skill.get('id', '')}: {e}")
            return False

    def executar_varredura(self, submolts: List[str] = None) -> Dict:
        """Pipeline completo de ingestão via Orchestrator."""
        if not self.enabled:
            return {"status": "disabled", "message": "Moltbook agent is disabled"}
            
        if not self.circuit_breaker.pode_executar():
            return {"status": "circuit_open", "message": "Mini Circuit Breaker está aberto."}
            
        submolts_to_scan = submolts if submolts else self.default_submolts
        stats = {"scanned_submolts": 0, "indexed_skills": 0, "errors": 0}
        
        try:
            for submolt in submolts_to_scan:
                logger.info(f"[MOLTBOOK] Varrendo submolt: {submolt}")
                skills = self.source.listar_skills(submolt)
                stats["scanned_submolts"] += 1
                
                # Take up to 5 per scan cycle
                for skill in skills[:5]:
                    if self._ingerir_skill(submolt, skill):
                        stats["indexed_skills"] += 1
                    else:
                        stats["errors"] += 1
                    time.sleep(1) # Slight delay between orchestrator calls
                    
            self.circuit_breaker.registrar_sucesso()
            return {"status": "success", "stats": stats}
            
        except DataSourceNotAvailable as e:
            logger.error(f"[MOLTBOOK] {e}")
            self.circuit_breaker.registrar_falha()
            return {"status": "error", "message": str(e)}
        except Exception as e:
            logger.error(f"[MOLTBOOK] Erro inesperado: {e}")
            self.circuit_breaker.registrar_falha()
            return {"status": "error", "message": str(e)}

    def _loop_ociosidade(self):
        # Evitar loop de imports circulares pesados
        try:
            from router_ai import detect_heavy_load
        except ImportError:
            def detect_heavy_load(): return False
            
        logger.info("[MOLTBOOK] Thread de ociosidade iniciada.")
        while self._running:
            try:
                heavy = detect_heavy_load()
                if heavy:
                    self._idle_consecutive_minutes = 0
                else:
                    self._idle_consecutive_minutes += 1
                    
                # 10 minutos (10 verificações de 60s) sem heavy load = Acionar
                if self._idle_consecutive_minutes >= 10:
                    logger.info("[MOLTBOOK] 10 min de ociosidade detectada. Iniciando varredura passiva.")
                    self.executar_varredura()
                    self._idle_consecutive_minutes = -350 # Esperar ~6 horas antes da próxima varredura
                    
            except Exception as e:
                logger.error(f"[MOLTBOOK] Erro no loop de ociosidade: {e}")
            time.sleep(60)

    def iniciar_modo_ocioso(self):
        if not self.enabled:
            return
        if self._ocioso_thread and self._ocioso_thread.is_alive():
            return
        self._running = True
        self._ocioso_thread = threading.Thread(target=self._loop_ociosidade, daemon=True)
        self._ocioso_thread.start()

    def parar_modo_ocioso(self):
        self._running = False
        
    def sinc_demanda(self) -> dict:
        """Varredura imediata acionada por comando MCP ou Dashboard."""
        logger.info("[MOLTBOOK] Sincronização Sob Demanda solicitada.")
        return self.executar_varredura()

# Exposição global para chamadas fáceis
_agent_instance = None
def get_moltbook_agent() -> MoltbookAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = MoltbookAgent()
    return _agent_instance
