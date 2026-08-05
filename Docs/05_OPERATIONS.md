# ⚙️ Manual de Operações & Manutenção — SparkHub v3.0

## 1. Modos de Execução

### 1.1 Maestro Daemon (Modo Persistente)
O orquestrador `sparkhub_master_live.py` roda por padrão como um daemon persistente, mantendo o controle de VRAM, CPU e ingestão de filas.

```cmd
python sparkhub_master_live.py
```

### 1.2 Modo de Teste Sintético
Para validar a fila anti-spam e o descarte gracioso sem manter o processo ativo:

```cmd
python sparkhub_master_live.py --test
```

### 1.3 Sessão Interativa + ngrok
Inicialização do servidor web na porta `8000` e estabelecimento do túnel HTTPS estático:

```cmd
iniciar_sparkhub.bat
```

---

## 2. Automação de Boot no Windows

O SparkHub v3.0 possui duas frentes independentes de auto-inicialização:

### 2.1 Boot Visual e de Ferramentas (MCP, Widget, Dashboard)
O núcleo do sistema interativo (`app.py`), o Widget (`sparkhub_systray.py`) e o Dashboard (`sparkhub_dashboard.py`) são inicializados no momento em que o usuário faz logon.
Isso é feito através de um VBScript silencioso localizado na pasta `Startup` do usuário:
- **Caminho do Script:** `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Start_SparkHub.vbs`
- **Comando interno:** `pythonw.exe D:\SparkHub\app.py`
- *Nota: O `app.py` gerencia ativamente os processos filhos de interface gráfica, escalonando o widget e disparando o dashboard através de processos em background (`subprocess.Popen` com `creationflags=CREATE_NO_WINDOW`).*

### 2.2 Boot do Maestro Daemon (Background via `schtasks`)
O registro de boot automático da coleta passiva é feito via `install_daemon.bat`:

```cmd
schtasks /create /tn "SparkHubMasterDaemon" /tr "pythonw \"%~dp0sparkhub_master_live.py\"" /sc onstart /f
```

- Para verificar a tarefa no Windows:
  ```cmd
  schtasks /query /tn "SparkHubMasterDaemon"
  ```
- Para excluir a tarefa:
  ```cmd
  schtasks /delete /tn "SparkHubMasterDaemon" /f
  ```

---

## 3. Diagnóstico e Resolução de Problemas

### 3.1 Verificação do Banco SQLite WAL
Se o banco `mempalace.db` parecer bloqueado:
```cmd
python -c "import sqlite3; conn = sqlite3.connect('mempalace.db'); print(conn.execute('PRAGMA journal_mode;').fetchone())"
```
*(Deve retornar `('wal',)`)*.

### 3.2 Logs do Quad-Channel Dispatcher
Verifique os logs de alertas gerados em tempo real:
- Log local de arquivo: `alerts.log`
- Notificações do IDE: `%USERPROFILE%\.gemini\antigravity\notifications.json`

## 3.3 Notas Operacionais Recentes
- O Roteador de IA foi externalizado para `router_ai.py`; a interface pública `app.route_ai_request` continua disponível para compatibilidade.
- Parâmetros de ambiente novos/úteis:
  - `PUPPETEER_EXECUTABLE` — caminho do executável do navegador para o gateway WhatsApp.
  - `WHATSAPP_QR_PATH` — caminho onde o QR do WhatsApp será salvo.
- Recomenda-se adicionar variáveis sensíveis ao `.env` local ou ao gerenciador de segredos e não commitar no repositório.

