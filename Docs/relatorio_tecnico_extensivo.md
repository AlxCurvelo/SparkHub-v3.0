# Relatório Técnico Extensivo: SparkHub (1 a 1)

Este documento contém o mapeamento de todos os módulos, classes e funções do sistema SparkHub.

## Módulo: `app.py`
### Classes
#### `class SparkHubTCPServer`
> (Sem documentação)

#### `class LocalHubMCPHandler`
> (Sem documentação)

**Métodos:**
- `_send_cors_headers(self)`
- `_send_json(self, status_code, data)`
- `_send_auth_error(self)`
- `_is_authenticated(self)`
- `do_HEAD(self)`
- `do_OPTIONS(self)`
- `do_GET(self)`
- `do_POST(self)`

### Funções Isoladas
- `init_state()`
- `find_available_port(start_port, max_tries)`
- `update_state(action, project_name, app_name, increment)`
- `auto_update_mapa_csv()`
  - *Varre os diretorios padrao de atalhos e executaveis do Windows e gera o mapa_executaveis.csv*
- `find_executable_or_shortcut(app_query)`
  - *Busca inteligente de atalhos/executaveis por correspondencia de nome*
- `launch_gui_app(app_cmd)`
  - *Utiliza os.startfile() nativo do Windows para disparar duplo clique direto no desktop do usuario*
- `parse_and_create_folder(text)`
  - *Detecta comandos de criacao de pastas em texto livre e cria o diretorio no disco D:*
- `get_recycle_bin_items()`
  - *Retorna os itens da Lixeira do Windows de forma instantanea*
- `init_mempalace()`
- `mempalace_save(wing, room, content)`
- `mempalace_search(query, wing)`
- `mempalace_list(wing, room, limit)`
- `mempalace_unlock(totp_code)`
- `detect_heavy_load()`
- `call_llm_api(url, payload, headers)`
- `route_ai_request(prompt, profile)`
- `load_env_phone()`
- `load_workspace_secret()`
- `proactive_memory_check(tool_name, args)`
- `execute_tool(name, args)`
  - *Executa as acoes nativas no Windows e MemPalace v3.0 com os.startfile(), Auto-Discovery, Auditoria e Contexto Proativo*

---

## Módulo: `audit_full.py`
---

## Módulo: `audit_migrated.py`
### Funções Isoladas
- `analyze_migrated_records()`

---

## Módulo: `check_data_loss.py`
### Funções Isoladas
- `test_data_loss()`

---

## Módulo: `check_db.py`
---

## Módulo: `clean_corrupted.py`
### Funções Isoladas
- `clean_database()`

---

## Módulo: `google_workspace_tools.py`
### Funções Isoladas
- `get_google_credentials()`
- `search_gmail(query, max_results)`
  - *Busca e-mails recentes correspondentes a uma query.*
- `search_drive(query, max_results)`
  - *Busca arquivos no Drive correspondentes a uma query e retorna metadata.*

---

## Módulo: `ingestao_drive.py`
**Descrição do Módulo:**
```text
ingestao_drive.py — Ingestão em Massa (Fase 1 / Caminho 1)

Varre Drive e Gmail (todas as contas conectadas via workspace_agent.py) e
grava resumos no MemPalace, pra que o ask_ai passe a "conhecer" esse
conteúdo sem precisar consultar a API do Google a cada pergunta.
```

### Funções Isoladas
- `mempalace_save(texto, categoria, origem)`
  - *Chamada real para salvar no banco de dados MemPalace. A API real usa: save_memory(wing, room, content)*
- `resumir(texto, limite)`
- `ingerir_gmail(query, max_por_conta)`
- `ingerir_drive(max_por_conta)`
- `main()`

---

## Módulo: `mempalace_autocollect_master.py`
**Descrição do Módulo:**
```text
SparkHub v3.0 - Coletor Proativo Multicanal (Nível 2 - Dados Reais)
Localização: D:\SparkHub\mempalace_autocollect_master.py
```

### Classes
#### `class AntifragileAutoCollectorV2`
> Coletor proativo Nível 2 com medição real de hardware e storage.

**Métodos:**
- `__init__(self, db_path)`
- `_get_conn(self)`
- `_init_db(self)`
- `save_memory_if_new(self, wing, room, content)`
  - *Salva a memória apenas se o conteúdo for inédito (Deduplicação).*
- `collect_real_disk_guard(self)`
- `collect_real_storage_parser(self)`
- `collect_workspace_data(self)`
- `collect_shared_workspace_data(self)`
- `collect_google_docs(self)`
- `collect_devices_and_apps(self)`
- `collect_business_contacts(self)`
- `collect_browser_history_technical(self)`
- `collect_github_data(self)`
- `collect_moltbook_data(self)`

### Funções Isoladas
- `run_level3_collector()`

---

## Módulo: `migrate_sensitive_data.py`
### Funções Isoladas
- `is_text_sensitive(text)`
- `migrate_old_memories()`

---

## Módulo: `patch_app.py`
### Funções Isoladas
- `main()`

---

## Módulo: `patch_multi_mode.py`
### Funções Isoladas
- `main()`

---

## Módulo: `router_ai.py`
**Descrição do Módulo:**
```text
Router AI module extracted from app.py.
Contains the multi-mode AI router (Tríplice Cascata), detect_heavy_load and call_llm_api helpers.
```

### Funções Isoladas
- `detect_heavy_load()`
  - *Varre a lista de processos via tasklist e identifica se há apps pesados rodando.*
- `call_llm_api(url, payload, headers)`
- `route_ai_request(prompt, profile)`

---

## Módulo: `seed_mempalace.py`
**Descrição do Módulo:**
```text
SparkHub v3.0 - Script de Povoamento do MemPalace 
```

### Funções Isoladas
- `seed_mempalace(db_path)`

---

## Módulo: `setup_staging_quadchannel.py`
### Funções Isoladas
- `clear_terminal()`
- `setup_sparkhub()`

---

## Módulo: `sparkhub_audio_worker.py`
### Funções Isoladas
- `get_file_hash(filepath)`
- `process_audio_file(model, file_path)`
- `run_worker()`

---

## Módulo: `sparkhub_core.py`
**Descrição do Módulo:**
```text
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
```

### Classes
#### `class MicroStep`
> (Sem documentação)

#### `class StateManager`
> Fase 1: Gerenciamento de Estado com Checkpoint Seguro e Janela Deslizante.

**Métodos:**
- `__init__(self, state_file)`
- `load_state(self)`
  - *Carrega o checkpoint persistido do disco se existir.*
- `save_checkpoint(self, task_id, intent, current_idx, steps, payload, lock_timeout)`
  - *Salva o progresso atual com Escrita Atômica (Substituição Segura) e File Locking simples. Usa um arquivo de lock (state_file + '.lock') criado com O_EXCL para coordenar concorrência entre processos.*
- `prune_context(self, messages)`
  - *Mantém a Janela Deslizante limpa, preservando pares de Pergunta/Resposta para não criar "orfandade" de contexto.*

#### `class IntentPlanner`
> Fase 2: Decompositor de Intenção em Micro-Passos (Dinâmico).

**Métodos:**
- `decompose(self, user_request)`
  - *Converte uma intenção natural em uma fila atômica de micro-passos usando a Inteligência do SparkHub.*

---

## Módulo: `sparkhub_core_mcp.py`
**Descrição do Módulo:**
```text
SparkHub v3.0 - Core AI MCP Server (Porta Dinâmica)
Arquitetura Hexagonal: Contratos-First e UI-Agnostic
```

### Classes
#### `class MemorySearchContract`
> (Sem documentação)

#### `class SyncRequestContract`
> (Sem documentação)

#### `class AppOpenContract`
> (Sem documentação)

### Funções Isoladas
- `find_available_port(start_port, max_tries)`
- `search_mempalace(params)`
  - *Busca memórias e contextos no MemPalace usando os contratos Pydantic.*
- `sync_data(params)`
  - *Realiza sincronizações de dados baseadas nos contratos Pydantic.*
- `open_os_app(params)`
  - *Abre um app no SO via os.startfile (Arquitetura Hexagonal — Zero Mocks).*

---

## Módulo: `sparkhub_crypto.py`
### Classes
#### `class LockedException`
> (Sem documentação)

#### `class DATA_BLOB`
> (Sem documentação)

### Funções Isoladas
- `_get_machine_guid()`
- `dpapi_encrypt(data, entropy)`
- `dpapi_decrypt(data, entropy)`
- `get_totp_secret()`
- `check_rate_limit()`
- `record_failed_attempt()`
- `clear_failed_attempts()`
- `unlock_vault(totp_code)`
- `get_aes_key()`
- `encrypt_content(plaintext)`
- `decrypt_content(ciphertext)`
- `is_vault_unlocked()`

---

## Módulo: `sparkhub_dashboard.py`
### Funções Isoladas
- `login_required(f)`
- `login()`
- `check_port(host, port)`
- `get_disk_status()`
- `get_mempalace_stats()`
- `index()`
- `logs_page()`
- `api_logs()`
- `check_process(process_name)`
- `api_status()`
- `send_systray_signal(msg)`
  - *Envia sinal UDP IPC instantâneo para o Ícone de Bandeja do Windows (porta 8087).*
- `notify_pc_screen(title, message)`
  - *Exibe notificação Windows Toast no monitor do PC e imprime no console.*
- `launch_app_interactively(app_cmd)`
  - *Abre aplicativo interativamente na área de trabalho visível do Windows.*
- `api_chat()`
- `get_social_insights()`

---

## Módulo: `sparkhub_db.py`
**Descrição do Módulo:**
```text
SparkHub v3.0 - Unified Database & Resilience Engine (sparkhub_db.py)
Provides thread-safe, WAL-enabled SQLite persistence, automatic schema migration,
and safe transaction retries.
```

### Funções Isoladas
- `get_db_connection(db_path)`
  - *Returns a SQLite connection with WAL mode enabled and timeout configured.*
- `init_fts5_if_needed(db_path)`
  - *Configura o índice de busca BM25 (FTS5) se não existir.*
- `init_and_migrate_db(db_path)`
  - *Ensures all required tables and columns exist in mempalace.db.*
- `save_memory(wing, room, content, db_path)`
  - *Safely saves a memory entry into mempalace.db. Returns mem_id or 0 on failure.*
- `check_media_processed(file_hash, db_path)`
- `register_processed_media(file_hash, original_name, mem_id, db_path)`
- `save_chat_message(sender, message, response, channel, db_path)`
  - *Safely saves a chat interaction into chat_history and memories.*

---

## Módulo: `sparkhub_db_copy.py`
**Descrição do Módulo:**
```text
SparkHub v3.0 - Unified Database & Resilience Engine (sparkhub_db.py)
Provides thread-safe, WAL-enabled SQLite persistence, automatic schema migration,
and safe transaction retries.
```

### Funções Isoladas
- `get_db_connection(db_path)`
  - *Returns a SQLite connection with WAL mode enabled and timeout configured.*
- `init_fts5_if_needed(db_path)`
  - *Configura o índice de busca BM25 (FTS5) se não existir.*
- `init_and_migrate_db(db_path)`
  - *Ensures all required tables and columns exist in mempalace.db.*
- `save_memory(wing, room, content, db_path)`
  - *Safely saves a memory entry into mempalace.db.*
- `save_chat_message(sender, message, response, channel, db_path)`
  - *Safely saves a chat interaction into chat_history and memories.*

---

## Módulo: `sparkhub_embed_worker.py`
### Funções Isoladas
- `get_embedding(text)`
- `run_worker()`

---

## Módulo: `sparkhub_fastmcp.py`
**Descrição do Módulo:**
```text
SparkHub v3.0 - Pilar 1: FastMCP & SQLite RAG
Protocolo MCP (Model Context Protocol)
```

### Funções Isoladas
- `cosine_similarity(v1, v2)`
- `search_mempalace(query, limit)`
  - *Busca memórias e contextos no MemPalace do SparkHub usando Busca Híbrida (FTS5 BM25 + Semântica Vetorial). Use esta ferramenta para buscar informações sobre a vida do usuário, projetos, regras de sistema e tecnologias. Args: query: A palavra-chave ou termo de busca. limit: Número máximo de resultados de cada método.*
- `read_all_wings()`
  - *Retorna a lista de todas as categorias (Wings e Rooms) disponíveis no MemPalace. Útil para entender a estrutura de memória do SparkHub.*

---

## Módulo: `sparkhub_godot_blender.py`
### Classes
#### `class HeadlessOrchestrator`
> (Sem documentação)

**Métodos:**
- `__init__(self, blender_path)`
- `render_asset(self, script_path, use_gpu)`
- `_fallback_cpu_render(self, script_path)`

---

## Módulo: `sparkhub_ipc.py`
**Descrição do Módulo:**
```text
SparkHub v3.0 - Centralized IPC & Signal Manager (sparkhub_ipc.py)
Dispatches UDP signals (Processing, Operational, Error, Action) to the Systray Widget (Port 8087)
and manages inter-process communications securely.
```

### Funções Isoladas
- `send_systray_signal(state_or_cmd, details)`
  - *Sends a UDP packet to the Systray Widget on 127.0.0.1:8087. Supported states: 'yellow', 'green', 'red', 'blue', 'open_notepad', 'open_vscode', etc.*
- `notify_ide_quadchannel(title, message)`
  - *Appends notification to Antigravity IDE notifications.json atomically. (Quad-Channel Rule #4).*

---

## Módulo: `sparkhub_logger.py`
### Funções Isoladas
- `setup_logger(name)`

---

## Módulo: `sparkhub_master_live.py`
### Classes
#### `class CircuitBreaker`
> (Sem documentação)

**Métodos:**
- `__init__(self, name, timeout)`
- `trip(self, reason)`

#### `class QuadChannelDispatcher`
> Disparador atômico de alertas em 4 Canais (Toast, WhatsApp, Dashboard e IDE).

**Métodos:**
- `notify(insight_text)`

#### `class LiveOrchestrator`
> (Sem documentação)

**Métodos:**
- `__init__(self, db_path)`
- `detect_heavy_load(self)`
  - *Verifica se a GPU/Sistema está sobrecarregada (Simulação via CPU > 80%).*
- `trigger_godot_expression(self, expression_id)`
  - *Envia pacote UDP Não-Bloqueante para Godot 4 na porta 9000.*
- `trigger_obs_scene(self, scene_name)`
  - *Comunica com OBS via WebSocket v5 na porta 4455.*
- `generate_ai_response(self, prompt)`
  - *Roteamento real via Tríplice Cascata (app.route_ai_request).*
- `audit_memory(self, user, msg, ai_response)`
  - *Salva o resumo da interação na sala sync_audit do MemPalace.*
- `process_event_loop(self)`
  - *Loop Consumidor Isolado (Drop Older).*
- `simulate_tiktok_injection(self, count)`
  - *Simulador de estresse para validar o descarte de fila (Anti-Spam).*

---

## Módulo: `sparkhub_obs_tailscale.py`
### Classes
#### `class OBSBridgeManager`
> (Sem documentação)

**Métodos:**
- `__init__(self, host, port, password)`
- `send_command(self, request_type, data)`

---

## Módulo: `sparkhub_paths.py`
### Funções Isoladas
- `get_project_root()`
- `get_path()`
- `get_default_port(default_port)`

---

## Módulo: `sparkhub_reranker.py`
### Funções Isoladas
- `rerank_mempalace_results(query, results)`
  - *Atua como Especialista 6 (Rerank). Lê a lista bruta de resultados (híbridos) e reordena com base na relevância real da IA. results: list of tuples (wing, room, content, score_type) Returns: list of tuples reordenada (e possivelmente filtrada)*

---

## Módulo: `sparkhub_state_inspector.py`
### Classes
#### `class SystemStateInspector`
> (Sem documentação)

**Métodos:**
- `__init__(self, root_dir)`
- `audit_target(self, target_name, target_port)`

---

## Módulo: `sparkhub_sync_antifragil.py`
### Classes
#### `class CircuitBreakerState`
> (Sem documentação)

#### `class AntifragileBridge`
> (Sem documentação)

**Métodos:**
- `__init__(self, name)`
- `execute(self, func)`
- `_fallback_strategy(self)`

### Funções Isoladas
- `connect_obs_ws(port)`

---

## Módulo: `sparkhub_systray.py`
### Funções Isoladas
- `global_exception_handler(exc_type, exc_value, exc_traceback)`
- `load_config()`
- `save_config(x, y, w, h)`
- `draw_circle(state)`
- `animate_pulse()`
- `_apply_state(state)`
- `set_state(state)`
- `open_app(name)`
- `change_desktop_icon(icon_type)`
- `udp_server()`
- `show_menu(event)`
- `start_move(event)`
- `do_move(event)`
- `stop_move(event)`
- `start_resize(event)`
- `do_resize(event)`
- `stop_resize(event)`
- `on_enter(e)`
- `on_leave(e)`
- `main()`

---

## Módulo: `sparkhub_tiktok_chat.py`
### Classes
#### `class TikTokGhostReader`
> (Sem documentação)

**Métodos:**
- `__init__(self, username, db_path)`
- `_register_events(self)`
- `_save_memory(self, event_type, content)`
- `start(self)`

---

## Módulo: `sparkhub_verify.py`
**Descrição do Módulo:**
```text
sparkhub_verify.py

Modulo de Verificacao Real do SparkHub v3.0.
Implementa as 6 tecnicas de auditoria/depuracao definidas na secao 5 do AGENTS.md:

  1. Verificacao por execucao, nao por leitura (Empirical Verification)
  2. Rastreamento de causa raiz por tras dos imports (Root Cause Tracing)
  3. Ceticismo ativo contra "otimismo do modelo" (Adversarial Self-Review)
  4. Reconhecimento de padroes de codigo suspeitos (Static Code Smell Detection)
  5. Exigencia de evidencia bruta, nao resumo (Raw Evidence over Summary)
  6. Isolamento de variaveis (Bisection / Divide-and-Conquer)

Uso:
    python sparkhub_verify.py app.py
    python sparkhub_verify.py app.py --timeout 8
    python sparkhub_verify.py app.py --no-run     (soh testa imports + smell scan)

Filosofia: este script NUNCA declara algo "operacional". Ele so imprime
evidencia bruta (tracebacks reais, output real, lista de achados) e deixa
o veredito para quem le. Isso e proposital: a decisao de "esta corrigido"
deve ser humana ou baseada em criterio explicito, nao em auto-avaliacao do
proprio codigo que gerou o problema.
```

### Funções Isoladas
- `extract_top_level_imports(target_file)`
  - *Le o AST do arquivo e extrai os nomes dos modulos importados no topo, sem executar nada. Isso nos da a lista exata de dependencias a isolar.*
- `test_imports_isolated(target_file)`
  - *Tenta importar cada dependencia LOCAL (arquivo .py no mesmo diretorio) isoladamente, em subprocesso proprio, para que uma falha em um modulo nao mascare o resultado dos outros.*
- `run_and_capture(target_file, timeout)`
  - *Executa o script real, captura stdout+stderr linha a linha em tempo real.*
- `scan_for_smells(project_dir, self_path)`
- `build_report(target_file, import_results, run_result, smells)`
- `main()`

---

## Módulo: `sparkhub_vision_worker.py`
### Funções Isoladas
- `get_file_hash(filepath)`
- `encode_image(file_path)`
- `analyze_vision_media(file_path)`
- `run_worker()`

---

## Módulo: `sync_requisicoes_master.py`
### Classes
#### `class ProactiveNotifier`
> (Sem documentação)

**Métodos:**
- `__init__(self)`
- `trigger_async_alert(self, rejected_count, error_msg, disk_warning)`
- `_send_alert(self, rejected_count, error_msg, disk_warning)`

### Funções Isoladas
- `check_disk_guard()`
- `fetch_data_with_circuit_breaker()`
- `setup_databases()`
- `sync_data(conn_sync, data)`
- `audit_mempalace(conn_mem, count_upserted)`
- `main()`

---

## Módulo: `test.py`
---

## Módulo: `test_cascade.py`
### Funções Isoladas
- `test_failover()`

---

## Módulo: `test_crypto_flow.py`
### Funções Isoladas
- `test_crypto()`

---

## Módulo: `test_gemini_raw.py`
---

## Módulo: `verify_ingestion.py`
### Funções Isoladas
- `verify_new_ingestion()`

---

## Módulo: `whatsapp_gateway.py`
**Descrição do Módulo:**
```text
SparkHub - Gateway Local de WhatsApp (Opção B - Custo R$ 0,00)
Servidor HTTP leve em Python escutando em http://localhost:8082/send-whatsapp
```

### Classes
#### `class WhatsAppGatewayHandler`
> (Sem documentação)

**Métodos:**
- `do_GET(self)`
- `do_POST(self)`
- `log_message(self, format)`

### Funções Isoladas
- `run_whatsapp_gateway(port)`

---

## Módulo: `win32_antifragile.py`
**Descrição do Módulo:**
```text
SparkHub v3.0 - Pilar 4: Win32 API & Tailscale Antifrágil
Localização: sparkhub/win32_antifragile.py
```

### Classes
#### `class Win32Antifragile`
> Envelopamento de chamadas C++ para Win32 API protegidas contra crashes.

**Métodos:**
- `get_active_window_title()`
- `check_tailscale_ip()`
- `send_ghost_key(window_title, key_code)`

---

## Módulo: `workspace_agent.py`
### Funções Isoladas
- `init_db()`
- `registrar_requisicao(tipo, payload)`
- `atualizar_status(req_id, status)`
- `get_authenticated_service(api_name, version, token_file)`
- `add_new_account(alias)`
- `get_all_tokens()`
- `get_account_label(token_path)`
- `_clean_query(query_text)`
- `search_drive_docs(query_text)`
- `search_shared_drive_docs()`
- `search_all_google_docs()`
- `search_gmail(query_text)`
- `get_drive_file_fulltext(file_id, mime_type, token_path)`
- `get_gmail_full_message(msg_id, token_path)`
- `list_recent_gmail_ids(token_path, max_results, query)`
- `list_recent_drive_files(token_path, max_results)`
- `_parse_args()`
