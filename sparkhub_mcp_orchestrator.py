import time
import json
import hashlib
import logging
import uuid
import subprocess
import os
import traceback
import sparkhub_ipc
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from pydantic import BaseModel, Field

# Logger
logger = logging.getLogger("sparkhub_orchestrator")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s | %(levelname)-7s | [ORCHESTRATOR] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

# --- 3. Contratos de Dados (Pydantic) ---

class MCPRequest(BaseModel):
    request_id: str
    origin: str
    tool: str
    payload: dict
    timestamp: datetime
    ttl_seconds: int = 30

class CacheEntry(BaseModel):
    sha256: str
    response: dict
    cached_at: datetime
    hit_count: int = 1

class TelemetryRecord(BaseModel):
    request_id: str
    origin: str
    tool: str
    status: str
    latency_ms: float
    bytes_in: int
    bytes_out: int
    backend_used: str
    cache_hit: bool
    sha256: Optional[str] = None
    timestamp: datetime

# --- 4. Circuit Breaker ---

class CircuitBreaker:
    def __init__(self):
        # Backend -> Config
        self.configs = {
            "google_workspace_tools": {"timeout": 10, "max_fails": 3, "reset_time": 60},
            "mempalace": {"timeout": 2, "max_fails": 10, "reset_time": 15},
            "ask_ai": {"timeout": 15, "max_fails": 3, "reset_time": 120}  # Representa OpenRouter/DeepSeek/Gemini
        }
        # tool_name -> State
        self.states = {}

    def _get_config(self, tool_name: str) -> dict:
        if tool_name.startswith("google"):
            return self.configs["google_workspace_tools"]
        elif "mempalace" in tool_name:
            return self.configs["mempalace"]
        elif tool_name == "ask_ai":
            return self.configs["ask_ai"]
        # Default
        return {"timeout": 10, "max_fails": 3, "reset_time": 30}

    def check(self, tool_name: str) -> bool:
        """Retorna True se o circuito está ABERTO (rejeitar request)."""
        if tool_name not in self.states:
            return False
            
        state = self.states[tool_name]
        if state["status"] == "OPEN":
            config = self._get_config(tool_name)
            if time.time() - state["last_fail_time"] > config["reset_time"]:
                state["status"] = "HALF_OPEN"
                logger.info(f"Circuit Breaker para '{tool_name}' mudou para HALF_OPEN.")
                return False
            return True
        return False

    def record_success(self, tool_name: str):
        self.states[tool_name] = {"fails": 0, "last_fail_time": 0, "status": "CLOSED"}

    def record_failure(self, tool_name: str):
        if tool_name not in self.states:
            self.states[tool_name] = {"fails": 0, "last_fail_time": 0, "status": "CLOSED"}
            
        state = self.states[tool_name]
        state["fails"] += 1
        state["last_fail_time"] = time.time()
        
        config = self._get_config(tool_name)
        if state["fails"] >= config["max_fails"]:
            state["status"] = "OPEN"
            logger.error(f"Circuit Breaker ABERTO para '{tool_name}' após {state['fails']} falhas.")
            sparkhub_ipc.notify_ide_quadchannel(
                "Circuit Breaker Aberto",
                f"Backend {tool_name} indisponível. Circuito aberto por {config['reset_time']}s."
            )

# --- 5. Deduplicador ---

class Deduplicator:
    def __init__(self, window_seconds: int = 5):
        self.window_seconds = window_seconds
        self.cache: Dict[str, CacheEntry] = {}
        # TODO: Adicionar persistência SQLite para Cache como pede a Spec.

    def _clean_expired(self):
        now = datetime.now()
        expired = [k for k, v in self.cache.items() if (now - v.cached_at).total_seconds() > self.window_seconds]
        for k in expired:
            del self.cache[k]

    def get_hash(self, payload: dict) -> str:
        payload_str = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(payload_str.encode('utf-8')).hexdigest()

    def check_duplicate(self, payload: dict, origin: str) -> Optional[dict]:
        self._clean_expired()
        h = self.get_hash(payload)
        if h in self.cache:
            entry = self.cache[h]
            if (datetime.now() - entry.cached_at).total_seconds() <= self.window_seconds:
                entry.hit_count += 1
                logger.info(f"Requisição deduplicada (Cache HIT). Hash: {h[:8]}")
                if entry.hit_count % 5 == 0:
                    sparkhub_ipc.notify_ide_quadchannel(
                        "Spam Detectado",
                        f"Origem {origin} enviou {entry.hit_count} requisições duplicadas em {self.window_seconds}s."
                    )
                return entry.response
        return None

    def store(self, payload: dict, response: dict):
        h = self.get_hash(payload)
        self.cache[h] = CacheEntry(
            sha256=h,
            response=response,
            cached_at=datetime.now()
        )

# --- 6. Auto-Healer ---

class AutoHealer:
    def heal(self, tool_name: str, exception_msg: str) -> bool:
        """Tenta reerguer um serviço. Retorna True se deve retentar a requisição."""
        exception_lower = exception_msg.lower()
        
        # Heurística para Ollama local
        if tool_name == "ask_ai" and ("timeout" in exception_lower or "connection" in exception_lower or "winerror 10061" in exception_lower):
            if self._is_ollama_dead():
                logger.warning("Ollama não está rodando. Auto-Healing: Tentando subir `ollama serve`...")
                try:
                    # Inicia ollama serve em background (fire and forget)
                    subprocess.Popen(["C:\\OllamaPortable\\ollama.exe", "serve"], creationflags=subprocess.CREATE_NO_WINDOW)
                    time.sleep(3) # Dá um tempo para a porta abrir
                    return True
                except Exception as e:
                    logger.error(f"Falha ao reerguer Ollama: {e}")
                    
        # Heurística para MemPalace SQLite Lock
        elif "mempalace" in tool_name and "database is locked" in exception_lower:
            logger.warning("MemPalace bloqueado (WAL lock). Auto-Healing: Aguardando 500ms...")
            time.sleep(0.5)
            return True
            
        sparkhub_ipc.notify_ide_quadchannel(
            "Auto-Healing Falhou",
            f"Tentativa de reerguer {tool_name} falhou. Requer intervenção manual."
        )
        return False
        
    def _is_ollama_dead(self) -> bool:
        import psutil
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] and 'ollama' in proc.info['name'].lower():
                return False
        return True

# --- 7. Telemetria (SQLite Sync) ---

class Telemetry:
    def __init__(self):
        self.records = []
        # Conexão com sparkhub_db será feita pelo próprio app ou via módulo separado

    def log(self, record: TelemetryRecord):
        self.records.append(record)
        import sparkhub_db
        try:
            sparkhub_db.insert_telemetry(record.model_dump())
        except Exception as e:
            logger.error(f"Falha ao persistir telemetria no SQLite: {e}")

# --- ORCHESTRATOR PRINCIPAL ---

class MCPOrchestrator:
    def __init__(self):
        self.cb = CircuitBreaker()
        self.dedup = Deduplicator()
        self.healer = AutoHealer()
        self.telemetry = Telemetry()
        logger.info("SparkHub MCP Orchestrator Inicializado (Middleware Ativo).")

    def get_backend_name(self, tool_name: str) -> str:
        if tool_name == "ask_ai": return "router_ai"
        if tool_name.startswith("mempalace"): return "mempalace"
        if tool_name.startswith("google"): return "google_apis"
        return "system"

    def process(self, req: MCPRequest, execute_tool_func: Callable) -> dict:
        start_time = time.time()
        tool_name = req.tool
        backend = self.get_backend_name(tool_name)
        bytes_in = len(json.dumps(req.payload))
        
        # 2. Circuit Breaker
        if self.cb.check(tool_name):
            lat = (time.time() - start_time) * 1000
            self.telemetry.log(TelemetryRecord(
                request_id=req.request_id, origin=req.origin, tool=tool_name,
                status="circuit_open", latency_ms=lat, bytes_in=bytes_in, bytes_out=0,
                backend_used=backend, cache_hit=False, sha256=self.dedup.get_hash(req.payload), timestamp=datetime.now()
            ))
            # O contrato pede 503 HTTP, mas no contexto do JSON-RPC retornamos erro envelopado
            return {"error": {"code": 503, "message": f"Circuit Breaker OPEN para {tool_name}"}, "circuit": "open"}

        # 3. Deduplicador
        cached_resp = self.dedup.check_duplicate(req.payload, req.origin)
        if cached_resp:
            lat = (time.time() - start_time) * 1000
            bytes_out = len(json.dumps(cached_resp))
            self.telemetry.log(TelemetryRecord(
                request_id=req.request_id, origin=req.origin, tool=tool_name,
                status="completed", latency_ms=lat, bytes_in=bytes_in, bytes_out=bytes_out,
                backend_used=backend, cache_hit=True, sha256=self.dedup.get_hash(req.payload), timestamp=datetime.now()
            ))
            # Flag X-Cache será processada no do_POST se necessário
            return {"result": cached_resp, "_meta": {"x_cache": "HIT"}}

        # 4 & 5. Execução (Roteador) e Auto-Healing
        max_attempts = 3 if backend == "mempalace" else 2
        last_error = None
        result = None
        
        for attempt in range(max_attempts):
            try:
                # O execute_tool do app.py retorna uma string
                res_text = execute_tool_func(tool_name, req.payload.get("arguments", {}))
                self.cb.record_success(tool_name)
                result = {"content": [{"type": "text", "text": res_text}]}
                break
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Falha na execução de {tool_name} (Tentativa {attempt+1})")
                logger.error(traceback.format_exc())
                
                # Tenta curar se não for a última tentativa
                if attempt < max_attempts - 1:
                    healed = self.healer.heal(tool_name, last_error)
                    if not healed:
                        # Se healer não sabe como curar isso, não adianta dar retry as cegas (exceto para retry puro configurado)
                        time.sleep(1) 
                
        if result is None:
            # Falha definitiva
            self.cb.record_failure(tool_name)
            lat = (time.time() - start_time) * 1000
            self.telemetry.log(TelemetryRecord(
                request_id=req.request_id, origin=req.origin, tool=tool_name,
                status="error", latency_ms=lat, bytes_in=bytes_in, bytes_out=0,
                backend_used=backend, cache_hit=False, sha256=self.dedup.get_hash(req.payload), timestamp=datetime.now()
            ))
            return {"error": {"code": -32603, "message": "Falha na execução interna do Orchestrator. Verifique os logs para mais detalhes."}}

        # 6. Telemetria e Retorno
        self.dedup.store(req.payload, result)
        
        lat = (time.time() - start_time) * 1000
        if lat > 5000:  # Limite de latência: 5s (5000ms)
            sparkhub_ipc.notify_ide_quadchannel(
                "Latência Anormal",
                f"Backend {backend} respondeu em {lat:.0f}ms (limite: 5000ms)."
            )
            
        bytes_out = len(json.dumps(result))
        self.telemetry.log(TelemetryRecord(
            request_id=req.request_id, origin=req.origin, tool=tool_name,
            status="completed", latency_ms=lat, bytes_in=bytes_in, bytes_out=bytes_out,
            backend_used=backend, cache_hit=False, sha256=self.dedup.get_hash(req.payload), timestamp=datetime.now()
        ))
        
        return {"result": result}

# Instância Singleton
orchestrator = MCPOrchestrator()
