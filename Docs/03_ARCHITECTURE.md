# 📐 Especificação Arquitetural — SparkHub v3.0

## 1. Visão Geral da Arquitetura Hexagonal

O SparkHub v3.0 adota uma Arquitetura Hexagonal (Ports & Adapters) UI-Agnostic, onde as regras de negócio centrais são completamente desacopladas de frameworks de interface, banco de dados ou provedores de IA.

```
       +-------------------------------------------------------+
       |                  Antigravity IDE                      |
       +-------------------------------------------------------+
                                   |
                          [FastMCP Porta 8000]
                                   v
+---------------------------------------------------------------------+
|                          CORE HEXÁGONO                              |
|                                                                     |
|   +-----------------------+       +-----------------------------+   |
|   | AppOpenContract       |       | SyncRequestContract         |   |
|   +-----------------------+       +-----------------------------+   |
|                                                                     |
|   +-------------------------------------------------------------+   |
|   |                    Tríplice Cascata                         |   |
|   |         Ollama (Local) ➔ OpenRouter ➔ Gemini                |   |
|   +-------------------------------------------------------------+   |
+---------------------------------------------------------------------+
          |                          |                        |
          v                          v                        v
  +---------------+          +---------------+        +---------------+
  |  mempalace.db |          | Quad-Channel  |        | Auto-Discovery|
  |  (SQLite WAL) |          | Dispatcher    |        | Windows Shell |
  +---------------+          +---------------+        +---------------+
```

---

## 2. Componentes Principais

### 2.1 FastMCP Server (`sparkhub_core_mcp.py`)
- **Protocolo:** Model Context Protocol (FastMCP) sobre STDIO e SSE.
- **Porta padrão:** `:8000`.
- **Validação de Inputs:** Modelos Pydantic (`AppOpenContract`, `SyncRequestContract`).
- **Zero Mocks:** Abertura de aplicativos integrada via `os.startfile()` e `subprocess.Popen()`.

### 2.2 Tríplice Cascata de IA (router_ai.py)
Roteamento inteligente de inferência de linguagem com failover automatizado. A implementação foi extraída para `router_ai.py` para melhorar modularidade e testabilidade. A API pública para consumidores externos permanece disponível via `app.route_ai_request` que delega para `router_ai.route_ai_request`.

1. **Primeira Camada (Local / Gratuito):** Ollama `llama3:latest` (privacidade total e latência ultrabaixa).
2. **Segunda Camada (Nuvem Intermediária):** OpenRouter API (`mistralai/` ou `anthropic/`).
3. **Terceira Camada (Nuvem Avançada / Fallback):** Google Gemini API (`gemini-2.5-flash` ou `gemini-1.5-pro`).

Nota: Extração do roteador permite testes unitários e uma futura remoção segura do código duplicado em `app.py` após validação em staging.
### 2.3 Auto-Discovery de Softwares
- Varredura de atalhos em `C:\ProgramData\...`, `%APPDATA%\...`, `Desktop` e `Program Files`.
- Mapeamento dinâmico no arquivo indexado `mapa_executaveis.csv`.
- Resolução fuzzy em tempo real via `find_executable_or_shortcut()`.

### 2.4 Quad-Channel Dispatcher
Sistema antifrágil de eventos e alertas estruturado em 4 canais isolados:
- **Canal 1:** Windows Toast Notification nativo (PowerShell / .NET).
- **Canal 2:** Webhooks assíncronos (Discord / Telegram).
- **Canal 3:** Gravação atômica em `alerts.log`.
- **Canal 4:** Notificações JSON em `%USERPROFILE%\.gemini\antigravity\notifications.json`.
# 📐 Especificação Arquitetural — SparkHub v3.0

## 1. Visão Geral da Arquitetura Hexagonal

O SparkHub v3.0 adota uma Arquitetura Hexagonal (Ports & Adapters) UI-Agnostic, onde as regras de negócio centrais são completamente desacopladas de frameworks de interface, banco de dados ou provedores de IA.

```
        +-------------------------------------------------------+
        |                  Antigravity IDE                      |
        +-------------------------------------------------------+
                                    |
                           [FastMCP Porta 8000]
                                    v
+---------------------------------------------------------------------+
|                          CORE HEXÁGONO                              |
|                                                                     |
|   +-----------------------+       +-----------------------------+   |
|   | AppOpenContract       |       | SyncRequestContract         |   |
|   +-----------------------+       +-----------------------------+   |
|                                                                     |
|   +-------------------------------------------------------------+   |
|   |                    Tríplice Cascata                         |   |
|   |         Ollama (Local) ➔ OpenRouter ➔ Gemini                |   |
|   +-------------------------------------------------------------+   |
+---------------------------------------------------------------------+
           |                          |                        |
           v                          v                        v
   +---------------+          +---------------+        +---------------+
   |  mempalace.db |          | Quad-Channel  |        | Auto-Discovery|
   |  (SQLite WAL) |          | Dispatcher    |        | Windows Shell |
   +---------------+          +---------------+        +---------------+
```

---

## 2. Componentes Principais

### 2.1 FastMCP Server (`sparkhub_core_mcp.py`)
- **Protocolo:** Model Context Protocol (FastMCP) sobre STDIO e SSE.
- **Porta padrão:** `:8000`.
- **Validação de Inputs:** Modelos Pydantic (`AppOpenContract`, `SyncRequestContract`).
- **Zero Mocks:** Abertura de aplicativos integrada via `os.startfile()` e `subprocess.Popen()`.

### 2.2 Tríplice Cascata de IA (`router_ai.py`)
Roteamento inteligente de inferência de linguagem com failover automatizado. A implementação foi extraída para `router_ai.py` para melhorar modularidade e testabilidade. A API pública para consumidores externos permanece disponível via `app.route_ai_request` que delega para `router_ai.route_ai_request`.

1. **Primeira Camada (Local / Gratuito):** Ollama `llama3:latest` (privacidade total e latência ultrabaixa).
2. **Segunda Camada (Nuvem Intermediária):** OpenRouter API (`mistralai/` ou `anthropic/`).
3. **Terceira Camada (Nuvem Avançada / Fallback):** Google Gemini API (`gemini-2.5-flash` ou `gemini-1.5-pro`).

Nota: Extração do roteador permite testes unitários e uma futura remoção segura do código duplicado em `app.py` após validação em staging.

### 2.3 Auto-Discovery de Softwares
- Varredura de atalhos em `C:\ProgramData\...`, `%APPDATA%\...`, `Desktop` e `Program Files`.
- Mapeamento dinâmico no arquivo indexado `mapa_executaveis.csv`.
- Resolução fuzzy em tempo real via `find_executable_or_shortcut()`.

### 2.4 Quad-Channel Dispatcher
Sistema antifrágil de eventos e alertas estruturado em 4 canais isolados:
- **Canal 1:** Windows Toast Notification nativo (PowerShell / .NET).
- **Canal 2:** Webhooks assíncronos (Discord / Telegram).
- **Canal 3:** Gravação atômica em `alerts.log`.
- **Canal 4:** Notificações JSON em `%USERPROFILE%\.gemini\antigravity\notifications.json`.

```mermaid
flowchart LR
    subgraph Core
        A[FastMCP Server (sparkhub_core_mcp.py)]
    end
    subgraph DB[Database Layer]
        B[sparkhub_db (SQLite WAL)]
    end
    subgraph IPC[IPC Layer]
        C[sparkhub_ipc (UDP Quad-Channel)]
        D[sparkhub_systray (Widget)]
    end
    subgraph AI[AI Router]
        E[router_ai.py]
    end
    A --> B
    A --> C
    C --> D
    E --> A
```

---
