# ⚡ SparkHub v3.0 Universal & Autonomous

> **Status:** 🟢 Ativo & Permanente (FastMCP + Quad-Channel + Tríplice Cascata + Daemon Boot)  
> **Repositório GitHub Oficial:** 🌐 [https://github.com/AlxCurvelo/SparkHub-v3.0](https://github.com/AlxCurvelo/SparkHub-v3.0)  
> **SSH Remote:** `git@github.com:AlxCurvelo/SparkHub-v3.0.git`  
> **Central de Documentação:** 📂 [`Docs/`](Docs/)

---

## 📚 Central Única de Documentação (`Docs/`)

Toda a documentação oficial do **SparkHub v3.0** está organizada na pasta [`Docs/`](Docs/):

| Documento | Conteúdo |
|---|---|
| 📄 **[`01_README.md`](Docs/01_README.md)** | Manual Geral, Módulos, Visão Arquitetural, MCP Tools e Quick Start. |
| 🛡️ **[`02_AGENTS.md`](Docs/02_AGENTS.md)** | Governança Canônica, Padrão Domain-Driven, Zero Mocks e Agente Oficial. |
| 📐 **[`03_ARCHITECTURE.md`](Docs/03_ARCHITECTURE.md)** | Arquitetura Hexagonal, FastMCP Porta 8000 e Roteador Tríplice Cascata. |
| 🧠 **[`04_MEMPALACE.md`](Docs/04_MEMPALACE.md)** | MemPalace Engine (SQLite WAL, FTS5/BM25, 39 Salas e Coleta Autônoma). |
| ⚙️ **[`05_OPERATIONS.md`](Docs/05_OPERATIONS.md)** | Manual de Operações, Daemon Boot (`schtasks`), Comandos e Logs. |
| 🚀 **[`06_DISTRIBUTION.md`](Docs/06_DISTRIBUTION.md)** | Guia do Pacote de Distribuição Limpa e Staging para Terceiros. |
| 🔍 **[`07_AUDIT_REPORT.md`](Docs/07_AUDIT_REPORT.md)** | Relatório Amplo de Auditoria de Engenharia e Verificação do Sistema. |
| 📋 **[`08_WALKTHROUGH.md`](Docs/08_WALKTHROUGH.md)** | Registro de Validações e Reparos Aplicados na Auditoria. |
| 📌 **[`09_IMPLEMENTATION_PLAN.md`](Docs/09_IMPLEMENTATION_PLAN.md)** | Plano Mestre de Implementação e Consolidação do Sistema. |

---

## 🚀 Como Executar Rápidamente

```cmd
# Executar o Maestro Orquestrador (Daemon Persistente)
python sparkhub_master_live.py

# Iniciar Sessão Interativa + ngrok Tunnel
iniciar_sparkhub.bat
```

## 📝 Atualizações Recentes (Resumo de mudanças aplicadas)

- Segurança: `.gitignore` atualizado para proteger tokens, credenciais e bancos locais (mempalace.db, sync_requisicoes.db, token*.json).
- Arquitetura: Roteador de IA extraído para `router_ai.py` (mantida compatibilidade de API via `app.route_ai_request`).
- Banco de Dados: Inicialização FTS5 centralizada em `sparkhub_db.py` e `get_db_connection` ajustada para concorrência.
- Estado: `StateManager.save_checkpoint` aprimorado com lockfile atômico para evitar condições de corrida.
- WhatsApp Gateway: Paths parametrizados via `PUPPETEER_EXECUTABLE` e `WHATSAPP_QR_PATH`; execs resolvidos com `path.resolve`.
- Robustez: Remoção de `sys.exit` em bibliotecas críticas, substituído por exceções tratáveis.

Para detalhes completos das alterações e próximos passos, consulte os documentos em `Docs/` e o todo registrado na base de tarefas (ID: `remove-router-duplicate`).
