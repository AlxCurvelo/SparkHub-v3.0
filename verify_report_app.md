# Relatorio de Verificacao Real -- app.py

> Este relatorio contem apenas evidencia bruta coletada por execucao
> real. Nenhuma linha abaixo declara "operacional" ou "corrigido" --
> essa e uma decisao humana, a ser tomada lendo a evidencia.

## 1. Teste isolado de imports locais (Bisection)
- `sparkhub_paths`: **OK**
- `router_ai`: **OK**
- `sparkhub_db`: **OK**
- `workspace_agent`: **OK**

## 2. Execucao real
- Veredito de execucao: **SERVIDOR_ATIVO**
- Exit code: `1`
- Output bruto capturado:
```
[AUTO-DISCOVERY] Mapeados 424 programas/atalhos em D:\SparkHub\mapa_executaveis.csv
=== SERVIDOR SPARKHUB v2.5.0 (SHELLEXECUTE / AUTO-DISCOVERY / CLI) RODANDO NA PORTA 8000 ===
Execucao nativa na sessao interativa com os.startfile() e auditoria pos-acao.
=== SERVIDOR SPARKHUB v2.5.0 RODANDO EM http://127.0.0.1:8000/ ===
```

## 3. Scanner de padroes suspeitos
### Achado 1
- Arquivo: `D:\SparkHub\app.py`
- Linha: 185
- Tipo: FString_Vazio
- Trecho: `full_cmd = f'start "" "{target}" ' + " ".join([f'"{a}"' if " " in str(a) else str(a) for a in extra_args])`
### Achado 2
- Arquivo: `D:\SparkHub\app.py`
- Linha: 191
- Tipo: FString_Vazio
- Trecho: `full_cmd = f'start "" "{target}"'`
### Achado 3
- Arquivo: `D:\SparkHub\app.py`
- Linha: 196
- Tipo: FString_Vazio
- Trecho: `subprocess.Popen(f'start "" "{app_cmd}"', shell=True)`
### Achado 4
- Arquivo: `D:\SparkHub\app.py`
- Linha: 272
- Tipo: FString_Vazio
- Trecho: `return f"Nenhuma memória encontrada para a busca '{query}'."`
### Achado 5
- Arquivo: `D:\SparkHub\app.py`
- Linha: 652
- Tipo: FString_Vazio
- Trecho: `print(f"[ORQUESTRADOR] Rota 2 (Status/Sync) ativada.")`
### Achado 6
- Arquivo: `D:\SparkHub\app.py`
- Linha: 662
- Tipo: FString_Vazio
- Trecho: `print(f"[ORQUESTRADOR] Rota 1 (Identidade) ativada.")`
### Achado 7
- Arquivo: `D:\SparkHub\app.py`
- Linha: 668
- Tipo: FString_Vazio
- Trecho: `print(f"[ORQUESTRADOR] Rota 3 (Workspace) ativada.")`
### Achado 8
- Arquivo: `D:\SparkHub\app.py`
- Linha: 687
- Tipo: FString_Vazio
- Trecho: `print(f"[ORQUESTRADOR] Injetando dados do Workspace na Rota 5...")`
### Achado 9
- Arquivo: `D:\SparkHub\app.py`
- Linha: 697
- Tipo: FString_Vazio
- Trecho: `print(f"[ORQUESTRADOR] Rota 4 (Ação SO) ativada para '{alvo}'.")`
### Achado 10
- Arquivo: `D:\SparkHub\app.py`
- Linha: 702
- Tipo: FString_Vazio
- Trecho: `print(f"[ORQUESTRADOR] Rota 5 (Raciocínio) ativada.")`
### Achado 11
- Arquivo: `D:\SparkHub\app.py`
- Linha: 715
- Tipo: FString_Vazio
- Trecho: `return finalize(f"Auto-Discovery encontrou para '{query}': {res_path}")`
### Achado 12
- Arquivo: `D:\SparkHub\app.py`
- Linha: 741
- Tipo: FString_Vazio
- Trecho: `return finalize(f"[✅ AUDITORIA SUCESSO] Programa '{app_target}' (ShellExecute: {resolved_app}) aceito pelo Windows e iniciado visível.")`
### Achado 13
- Arquivo: `D:\SparkHub\app.py`
- Linha: 1102
- Tipo: FString_Vazio
- Trecho: `print(f"=== SPARKHUB v2.5.0 MODO CLI ===")`
### Achado 14
- Arquivo: `D:\SparkHub\audit_full.py`
- Linha: 16
- Tipo: FString_Vazio
- Trecho: `'FStringEmpty': re.compile(r'f"[^\"]*\{\s*\}\s*"'),`
### Achado 15
- Arquivo: `D:\SparkHub\check_db.py`
- Linha: 17
- Tipo: FString_Vazio
- Trecho: `print(f"\nULTIMO CHAT:")`
### Achado 16
- Arquivo: `D:\SparkHub\mempalace_autocollect_master.py`
- Linha: 358
- Tipo: FString_Vazio
- Trecho: `msg = f"Pesquisa Web Técnica: '{title}' ({url})"`
### Achado 17
- Arquivo: `D:\SparkHub\mempalace_autocollect_master.py`
- Linha: 401
- Tipo: FString_Vazio
- Trecho: `msg = f"Repositório GitHub: '{name}' (Linguagem: {lang}) - {desc}"`
### Achado 18
- Arquivo: `D:\SparkHub\patch_app.py`
- Linha: 60
- Tipo: FString_Vazio
- Trecho: `return finalize(f"Auto-Discovery encontrou para '{query}': {res_path}")`
### Achado 19
- Arquivo: `D:\SparkHub\patch_app.py`
- Linha: 86
- Tipo: FString_Vazio
- Trecho: `return finalize(f"[✅ AUDITORIA SUCESSO] Programa '{app_target}' (ShellExecute: {resolved_app}) aceito pelo Windows e iniciado visível.")`
### Achado 20
- Arquivo: `D:\SparkHub\patch_app.py`
- Linha: 256
- Tipo: FString_Vazio
- Trecho: `print(f"=== SPARKHUB v2.5.0 MODO CLI ===")`
### Achado 21
- Arquivo: `D:\SparkHub\sparkhub_core.py`
- Linha: 203
- Tipo: FString_Vazio
- Trecho: `description=f"Falha ao decompor. Retorno LLM não foi JSON válido."`
### Achado 22
- Arquivo: `D:\SparkHub\sparkhub_core.py`
- Linha: 217
- Tipo: FString_Vazio
- Trecho: `print(f"\nDecompondo intenção: '{user_prompt}'")`
### Achado 23
- Arquivo: `D:\SparkHub\sparkhub_core.py`
- Linha: 231
- Tipo: FString_Vazio
- Trecho: `print(f"\n✅ Checkpoint atômico gravado em '{STATE_FILE_PATH}'.")`
### Achado 24
- Arquivo: `D:\SparkHub\sparkhub_core_mcp.py`
- Linha: 98
- Tipo: FString_Vazio
- Trecho: `result_str = f"🧠 Resultados MCP para '{params.query}':\n"`
### Achado 25
- Arquivo: `D:\SparkHub\sparkhub_core_mcp.py`
- Linha: 112
- Tipo: FString_Vazio
- Trecho: `msg = f"Sincronização do escopo '{params.scope}' acionada via porta MCP {MCP_PORT}. Force={params.force}"`
### Achado 26
- Arquivo: `D:\SparkHub\sparkhub_dashboard.py`
- Linha: 313
- Tipo: FString_Vazio
- Trecho: `ps_cmd = f"""`
### Achado 27
- Arquivo: `D:\SparkHub\sparkhub_dashboard.py`
- Linha: 336
- Tipo: FString_Vazio
- Trecho: `subprocess.Popen(["powershell", "-NoProfile", "-Command", f'Start-Process "{app_cmd}"'], creationflags=subprocess.CREATE_NO_WINDOW)`
### Achado 28
- Arquivo: `D:\SparkHub\sparkhub_dashboard.py`
- Linha: 341
- Tipo: FString_Vazio
- Trecho: `subprocess.Popen(f'start "" "{app_cmd}"', shell=True)`
### Achado 29
- Arquivo: `D:\SparkHub\sparkhub_dashboard.py`
- Linha: 361
- Tipo: FString_Vazio
- Trecho: `notify_pc_screen("📱 Comando do Celular Recebido", f"Instrução: '{msg_raw}'")`
### Achado 30
- Arquivo: `D:\SparkHub\sparkhub_fastmcp.py`
- Linha: 66
- Tipo: FString_Vazio
- Trecho: `result_str = f"🧠 Resultados do MemPalace para '{query}':\n"`
### Achado 31
- Arquivo: `D:\SparkHub\sparkhub_ipc.py`
- Linha: 36
- Tipo: FString_Vazio
- Trecho: `print(f"[IPC WARN] Could not deliver UDP signal '{state_or_cmd}': {e}")`
### Achado 32
- Arquivo: `D:\SparkHub\sparkhub_master_live.py`
- Linha: 38
- Tipo: FString_Vazio
- Trecho: `print(f"\n[QUAD-CHANNEL] Disparando Insight Moltbook para 4 canais...")`
### Achado 33
- Arquivo: `D:\SparkHub\sparkhub_master_live.py`
- Linha: 42
- Tipo: FString_Vazio
- Trecho: `ps_script = f"""`
### Achado 34
- Arquivo: `D:\SparkHub\sparkhub_systray.py`
- Linha: 67
- Tipo: FString_Vazio
- Trecho: `fill="#06060f", outline="")`
### Achado 35
- Arquivo: `D:\SparkHub\sparkhub_systray.py`
- Linha: 168
- Tipo: FString_Vazio
- Trecho: `print(f"[SYSTRAY] RAW UDP: '{raw}'")`
### Achado 36
- Arquivo: `D:\SparkHub\sparkhub_systray.py`
- Linha: 180
- Tipo: FString_Vazio
- Trecho: `print(f"[SYSTRAY] CMD PARSED: '{cmd}'")`
### Achado 37
- Arquivo: `D:\SparkHub\test_systray_debug.py`
- Linha: 15
- Tipo: FString_Vazio
- Trecho: `print(f"=== SparkHub Systray Debug Log ===")`
### Achado 38
- Arquivo: `D:\SparkHub\win32_antifragile.py`
- Linha: 62
- Tipo: FString_Vazio
- Trecho: `print(f"[WIN32-MURPHY] Janela '{window_title}' não encontrada para injeção.")`
### Achado 39
- Arquivo: `D:\SparkHub\workspace_agent.py`
- Linha: 116
- Tipo: FString_Vazio
- Trecho: `print(f"[*] Starting OAuth flow for account '{alias}' …")`
### Achado 40
- Arquivo: `D:\SparkHub\workspace_agent.py`
- Linha: 118
- Tipo: FString_Vazio
- Trecho: `print(f"[✔] Account '{alias}' connected! Token saved at {token_path}")`
### Achado 41
- Arquivo: `D:\SparkHub\workspace_agent.py`
- Linha: 170
- Tipo: FString_Vazio
- Trecho: `drive_query = " and ".join([f"name contains '{p}'" for p in palavras]) + " and trashed=false"`
### Achado 42
- Arquivo: `D:\SparkHub\workspace_agent.py`
- Linha: 171
- Tipo: FString_Vazio
- Trecho: `full_query = " and ".join([f"fullText contains '{p}'" for p in palavras]) + " and trashed=false"`
### Achado 43
- Arquivo: `D:\SparkHub\whatsapp-bot\package-lock.json`
- Linha: 1145
- Tipo: FString_Vazio
- Trecho: `"setprototypeof": "1.2.0",`
### Achado 44
- Arquivo: `D:\SparkHub\whatsapp-bot\package-lock.json`
- Linha: 1497
- Tipo: FString_Vazio
- Trecho: `"setprototypeof": "~1.2.0",`

## Leitura sugerida (nao e veredito automatico)
- O processo subiu e emitiu um sinal de servidor/daemon ativo; foi
  encerrado deliberadamente por este script apos a confirmacao (exit
  code negativo aqui e esperado -- e o sinal de terminate, nao um erro).
  Isso NAO prova que os endpoints respondem corretamente -- teste-os
  com uma chamada real (ex: curl) enquanto o processo estiver rodando.