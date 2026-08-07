# SparkHub v3.0 - Changelog de Arquitetura

## Novas Funcionalidades e Agentes

### 1. Orchestrator Central (Porta 8000)
- **Barramento MCP Seguro:** Todas as ferramentas e rotinas críticas agora passam por sparkhub_mcp_orchestrator.py.
- **Telemetria:** Log de metadados em SQLite para todas as operações sem expor payloads (Zero Data Leak).
- **Deduplicação (SHA-256):** Requisições idênticas em uma janela de 5 segundos são oxigenadas diretamente do cache em memória.
- **Circuit Breaker Global:** Impede cascatas de erro, respondendo HTTP 503 imediatamente se o backend falhar repetidamente.

### 2. Search-Augmented Prompt (Busca Desacoplada)
- O sparkhub_search_agent.py assumiu a responsabilidade exclusiva pelas buscas (search_gmail, search_drive_docs, mempalace_search).
- **Modo Híbrido Anti-Frágil:**
  1. Tenta a busca via Orchestrator (Porta 8000).
  2. Acelera com Cache Local (SHA-256).
  3. Aciona Fallback Direct (import nativo) se o Orchestrator cair.
  4. Protege a cota da Google com um Mini Circuit Breaker Local (trava após 3 falhas).
- Os LLMs da Tríplice Cascata agora recebem o contexto já mastigado e não executam mais Tool Calls, eliminando loops e timeouts.

### 3. Agente de Ingestão Moltbook (Fonte Passiva)
- **Modo Ocioso:** O sparkhub_moltbook_agent.py monitora o detect_heavy_load() e inicia varreduras silenciosas após 10 minutos de inatividade do PC.
- **Abordagem B (Interfaces):** Infraestrutura pronta com LocalDirectorySource e HTTPEndpointSource.
- **Zero Mocks:** A fonte HTTP possui uma trava lógica que impede seu carregamento se o endpoint real não for fornecido.
- A ingestão passa obrigatoriamente pelo Orchestrator (mempalace_save) para deduplicação e telemetria.

### 4. GDD - Game Design Document
- A semente estrutural do GDD foi criada em gdd.md, pavimentando o caminho para o uso final da engine (Godot 4.x).
