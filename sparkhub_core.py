"""
GDD-INLINE: SparkHub Core Architecture - Fase 1 (State) & Fase 2 (Planner)
-------------------------------------------------------------------------------
[OBJETIVO]:
  Prover gerenciamento de estado atômico (Janela Deslizante + Checkpoint) e 
  decomposição automática de intenções em micro-passos (T1) para o SparkHub.

[CONTRATOS DE DADOS]:
  - MicroStep: {
      "step_id": str,
      "action_type": "CREATE_FILE" | "EXECUTE_CMD" | "CREATE_DIR" | "INSPECT",
      "target_path": str,
      "description": str,
      "status": "PENDING" | "SUCCESS" | "FAILED"
    }
  - TaskState: {
      "task_id": str,
      "user_intent": str,
      "current_step_index": int,
      "steps": List[MicroStep],
      "payload": dict
    }

[REGRAS DE NEGÓCIO]:
  1. O cabeçalho GDD-INLINE deve ser mantido intacto pela IA (prevenção de amnésia).
  2. Cada micro-passo é salvo em 'task_state.json' de forma ATÔMICA e segura.
  3. O histórico de mensagens é mantido preservando pares Pergunta/Resposta.
  4. O estado persistido permite retomar execuções interrompidas sem refazer etapas.
-------------------------------------------------------------------------------
"""

import json
import os
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

from sparkhub_paths import get_path

# Importando o roteador multi-mode já construído
try:
    from app import route_ai_request
except ImportError:
    # Fallback/Mock caso o app.py não consiga ser importado no teste isolado
    def route_ai_request(prompt, profile="auto"):
        return "{}"

# --- CONSTANTES DE CONFIGURAÇÃO ---
STATE_FILE_PATH = str(get_path("task_state.json"))
MAX_HISTORY_PAIRS = 2 # Quantidade máxima de PARES (User + Assistant) a manter


@dataclass
class MicroStep:
    step_id: str
    action_type: str
    target_path: str
    description: str
    status: str = "PENDING"


class StateManager:
    """Fase 1: Gerenciamento de Estado com Checkpoint Seguro e Janela Deslizante."""

    def __init__(self, state_file: str = STATE_FILE_PATH):
        self.state_file = state_file

    def load_state(self) -> Optional[Dict[str, Any]]:
        """Carrega o checkpoint persistido do disco se existir."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return None
        return None

    def save_checkpoint(self, task_id: str, intent: str, current_idx: int, steps: List[MicroStep], payload: Dict[str, Any], lock_timeout: float = 5.0):
        """Salva o progresso atual com Escrita Atômica (Substituição Segura) e File Locking simples.

        Usa um arquivo de lock (state_file + '.lock') criado com O_EXCL para coordenar concorrência entre processos.
        """
        data = {
            "task_id": task_id,
            "user_intent": intent,
            "current_step_index": current_idx,
            "steps": [asdict(s) for s in steps],
            "payload": payload
        }

        os.makedirs(os.path.dirname(self.state_file) or ".", exist_ok=True)
        temp_file = self.state_file + ".tmp"
        lock_file = self.state_file + ".lock"

        start = time.time()
        fd = None
        try:
            # Acquire simple exclusive lock by atomically creating the lock file
            while True:
                try:
                    fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                    # Lock acquired
                    break
                except FileExistsError:
                    if (time.time() - start) > lock_timeout:
                        raise TimeoutError(f"Could not acquire state lock for {self.state_file} after {lock_timeout}s")
                    time.sleep(0.05)

            # Escrita Atômica com tentativa de retry (evitar concorrência)
            retries = 3
            for attempt in range(retries):
                try:
                    with open(temp_file, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    os.replace(temp_file, self.state_file)
                    break
                except PermissionError:
                    time.sleep(0.1) # Aguarda se outro processo estiver lendo/escrevendo
        finally:
            # Release lock
            try:
                if fd is not None:
                    os.close(fd)
                if os.path.exists(lock_file):
                    os.remove(lock_file)
            except Exception:
                pass

    def prune_context(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Mantém a Janela Deslizante limpa, preservando pares de Pergunta/Resposta 
        para não criar "orfandade" de contexto.
        """
        if not messages:
            return messages

        system_msg = messages[0] if messages[0].get("role") == "system" else None
        chat_turns = messages[1:] if system_msg else messages

        # Garante que o histórico sempre comece num 'user' e conte PARES
        # Ex: se MAX_HISTORY_PAIRS = 2, mantém no máximo as últimas 4 mensagens
        max_messages = MAX_HISTORY_PAIRS * 2
        if len(chat_turns) > max_messages:
            chat_turns = chat_turns[-max_messages:]
            # Se a primeira mensagem pós-corte for do assistente, descartamos para não orfanar
            if chat_turns[0].get("role") == "assistant":
                chat_turns = chat_turns[1:]

        return [system_msg] + chat_turns if system_msg else chat_turns


class IntentPlanner:
    """Fase 2: Decompositor de Intenção em Micro-Passos (Dinâmico)."""

    def decompose(self, user_request: str) -> List[MicroStep]:
        """
        Converte uma intenção natural em uma fila atômica de micro-passos usando a Inteligência do SparkHub.
        """
        system_prompt = (
            "Você é o IntentPlanner do SparkHub. Transforme a intenção do usuário em passos estritos.\n"
            "Retorne APENAS UM ARRAY JSON VÁLIDO. Sem formatações markdown.\n"
            "Exemplo:\n"
            '[\n'
            '  {"step_id": "step_1", "action_type": "CREATE_DIR", "target_path": "D:\\\\SparkHub\\\\novo", "description": "Criar pasta"},\n'
            '  {"step_id": "step_2", "action_type": "CREATE_FILE", "target_path": "D:\\\\SparkHub\\\\novo\\\\app.py", "description": "Criar arquivo"}\n'
            ']\n\n'
            f"INTENÇÃO DO USUÁRIO: {user_request}"
        )
        
        # Delega para o Roteador Multi-Mode (Nuvem ou Local)
        raw_response = route_ai_request(system_prompt, profile="auto")
        print("DEBUG RAW RESPONSE:", repr(raw_response))
        import re
        
        # O roteador injeta tags como "[☁️ CLOUD_PROXY: Gemini]\n". Removemos isso.
        if "]\n" in raw_response:
            raw_response = raw_response.split("]\n", 1)[1].strip()

        # Regex específica para encontrar o início de um array JSON [ { ... } ]
        match = re.search(r'\[\s*\{.*?\}\s*\]', raw_response, re.DOTALL)
        if match:
            cleaned_json = match.group(0)
        else:
            cleaned_json = raw_response

        steps: List[MicroStep] = []
        try:
            parsed = json.loads(cleaned_json)
            for item in parsed:
                steps.append(MicroStep(
                    step_id=item.get("step_id", f"step_{len(steps)+1}"),
                    action_type=item.get("action_type", "INSPECT"),
                    target_path=item.get("target_path", ""),
                    description=item.get("description", ""),
                    status="PENDING"
                ))
        except json.JSONDecodeError:
            # Fallback de segurança se o LLM falhar miseravelmente na formatação
            steps.append(MicroStep(
                step_id="step_fail",
                action_type="INSPECT",
                target_path="D:\\SparkHub",
                description=f"Falha ao decompor. Retorno LLM não foi JSON válido."
            ))

        return steps


# --- TESTE ATÔMICO DE EXECUÇÃO ---
if __name__ == "__main__":
    print("🚀 Testando Módulos SparkHub Core (Escrita Atômica + Planejador Dinâmico)...")

    state_mgr = StateManager()
    planner = IntentPlanner()

    user_prompt = "Criar pasta temp_tests e um arquivo log.txt dentro dela"
    print(f"\nDecompondo intenção: '{user_prompt}'")
    micro_steps = planner.decompose(user_prompt)
    
    for step in micro_steps:
        print(f" -> [{step.action_type}] {step.target_path} : {step.description}")

    state_mgr.save_checkpoint(
        task_id="task_001",
        intent=user_prompt,
        current_idx=0,
        steps=micro_steps,
        payload={"env": "Windows 11", "status": "INITIALIZED"}
    )

    print(f"\n✅ Checkpoint atômico gravado em '{STATE_FILE_PATH}'.")
