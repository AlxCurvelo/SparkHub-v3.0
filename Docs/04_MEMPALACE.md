# 🧠 MemPalace Engine — Manual Técnico & Especificações

> **Banco de Dados:** `mempalace.db`  
> **Modo de Concorrência:** Write-Ahead Logging (WAL)  
> **Algoritmo de Busca:** FTS5 (Full-Text Search 5) com ranking BM25  

---

## 1. Estrutura do Banco de Dados

O `mempalace.db` é o acervo permanente de memória de longo prazo do SparkHub v3.0, operando sob o modo WAL para garantir leitura concorrente contínua sem bloqueio de gravação.

### Tabela de Memórias (`memories`)
- `id` (INTEGER PRIMARY KEY)
- `content` (TEXT) — Conteúdo bruto da memória/insight.
- `room` (TEXT) — Sala temática de classificação.
- `created_at` (DATETIME) — Carimbo de data/hora de criação.

---

## 2. Estatísticas do Acervo (305 Memórias em 39 Salas)

| Sala Temática | Finalidade | Qtd. Memórias |
|---|---|---|
| `web_research_insights` | Insights coletados via web e feeds autônomos | 87 |
| `google_docs` | Metadados e resumos de documentos do Google Docs | 38 |
| `sync_audit` | Logs de sincronização e auditoria de sistemas | 24 |
| `android_and_pc_registrations` | Mapeamento de dispositivos e aplicativos | 23 |
| `drive_docs` | Indexação de arquivos do Google Drive | 22 |
| `gmail_notifications` | Alertas e e-mails processados | 18 |
| `system_status` / `alerts` | Status de hardware, VRAM e alertas do sistema | 26 |
| *Outras 32 salas* | Categorias especializadas (família, dev, hardware, etc.) | 67 |

---

## 3. Coleta Autônoma (`mempalace_autocollect_master.py`)

O script autônomo opera em background e realiza as seguintes rotinas de coleta passiva:
1. **Drive & Gmail Sweeper:** Leitura e indexação autônoma via API Google (com suporte a token portável).
2. **System Health Check:** Coleta periódica de telemetria de disco (`DiskGuard`) e recursos do Windows.
3. **Escrita Atômica:** Inserção em lote no `mempalace.db` com controle de integridade WAL.

---

## 4. Consultas FTS5 e Ferramentas MCP

A consulta no acervo é exposta nativamente via MCP (`sparkhub_core_mcp.py`):

```python
# Consulta com ranking BM25
SELECT content, room, bm25(memories_fts) AS rank 
FROM memories_fts 
WHERE memories_fts MATCH ? 
ORDER BY rank LIMIT 10;
```
