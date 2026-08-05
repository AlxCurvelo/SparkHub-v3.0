# 🛡️ Governança Canônica: Google Antigravity & SparkHub v3.0

O Google Antigravity atua como o **Agent Manager** primário e a IDE unificada do ecossistema SparkHub v3.0. Todas as execuções de sub-agentes, rotinas autônomas e testes sintéticos devem seguir estritamente as diretrizes abaixo.

---

## 1. Padrão Domain-Driven e Contratos-First
- Todos os sub-agentes não devem injetar dados "mockados" sob nenhuma circunstância. A regra é **Zero Mocks**.
- As requisições de serviço (como sincronização, buscas, etc.) devem operar unicamente através das interfaces padronizadas (Hexágono Externo), utilizando os modelos Pydantic definidos.
- A orquestração das requisições deve priorizar o uso das portas MCP (Barramento FastMCP).

## 2. Agente Oficial: `SyncRequisicoesAgent`
- O agente oficial `SyncRequisicoesAgent` é o guardião responsável por orquestrar a conciliação de dados locais (`LOCAL_API`) e na nuvem (`GOOGLE_SHEETS`).
- Em suas rotinas, o agente não deve assumir estados arbitrários. Se um endpoint falhar, o agente deve assumir o conceito de *Fail-Fast* e reportar graciosamente via Quad-Channel Dispatcher.

## 3. Integração com o Quad-Channel Dispatcher
- Todas as detecções, anomalias e novos insights gerados por agentes devem ser despachados no arquivo local da IDE (Canal 4).
- O log/notificação deve ser inserido de forma atômica no arquivo `%USERPROFILE%\.gemini\antigravity\notifications.json`, no formato estruturado especificado no Dispatcher.
- Agentes devem respeitar o limite de recursos e desviar processamentos pesados para a nuvem usando a **Tríplice Cascata** (via `app.py`).

## 4. Filosofia Operacional
- **A mente governa, a máquina trabalha.** Todo comportamento automatizado deve servir ao painel *Mission Control* sem exigir constante aprovação de micro-passos para operações de coleta passiva.
- Agentes podem ser disparados silenciosamente pela IDE para manter o banco `mempalace.db` aquecido (Modo WAL ativado).

## Regras de Auditoria de Código (Anti-Alucinação)

1. NUNCA declarar um módulo "operacional" ou "100% funcional" sem 
   executá-lo de fato e mostrar o output real do terminal.
2. Ao gerar relatórios de auditoria, ler o CORPO das funções, não 
   apenas verificar docstrings/estilo. Rastrear cada valor sensível 
   (tokens, chaves, headers) até sua origem.
3. Procurar ativamente por padrões suspeitos: strings literais como 
   "******", "TODO", "PLACEHOLDER", f-strings sem variáveis interpoladas, 
   valores hardcoded que deveriam ser dinâmicos.
4. Ao "sanitizar" credenciais para distribuição, nunca substituir a 
   REFERÊNCIA à variável (ex: `openrouter_key`) — só remover valores 
   hardcoded reais. Testar após qualquer sanitização.
5. Um teste só conta como "PASS" se rodou o código de ponta a ponta 
   com uma chamada real, não apenas checou schema ou sintaxe.

## 5. Padrão de Verificação Real (Anti-Alucinação de Status)

Toda tarefa de refatoração, correção de bug ou auditoria só pode ser marcada como
"Concluída", "Corrigida" ou "Operacional" se satisfizer TODAS as condições abaixo.
Nenhuma exceção, mesmo sob pressão de prazo ou pedido do usuário.

### 5.1 Prova de Execução Real

- Scanners estáticos (verificação de sintaxe, docstrings, padrões de texto como
`audit_full.py`) NUNCA são suficientes sozinhos para declarar algo "funcional".
Eles só provam ausência de um padrão específico, não presença de comportamento correto.
- Toda correção de lógica (ex: chamadas de API, roteamento, banco de dados) exige
uma execução real da função/endpoint afetado, com o **output completo colado
no relatório** — não um resumo do tipo "PASS ✅" sem evidência.
- Chamadas de rede/API devem mostrar o corpo real da resposta (ou erro real),
nunca apenas "sem exceção lançada".

### 5.2 Proibição de Auto-Sanitização Silenciosa de Segredos

- Ao remover/mascarar credenciais para distribuição, NUNCA substituir a referência
à variável (ex: `openrouter_key`, `api_key`) por um literal mascarado
(ex: `"******"`) dentro de código que efetivamente usa esse valor em runtime.
Isso quebra a funcionalidade silenciosamente.
- Após qualquer sanitização de segredos, rodar um teste funcional que dependa
daquele segredo, confirmando que ele ainda é lido corretamente da variável
de ambiente/`.env`.

### 5.3 Sinais de Alerta a Serem Ativamente Procurados

Ao revisar ou gerar código, sinalizar explicitamente (não apenas corrigir em
silêncio) qualquer ocorrência de:

- Strings literais suspeitas: `"******"`, `"TODO"`, `"PLACEHOLDER"`, `"FIXME"`
- F-strings sem nenhuma variável interpolada (`f"texto sem chaves {}"`)
- Efeitos colaterais no nível do módulo (código que roda automaticamente ao
importar um arquivo, fora de `if __name__ == "__main__":`)
- Testes que só verificam import/sintaxe, mas são reportados como "teste de
integração" ou "teste end-to-end"

### 5.4 Formato Obrigatório de Relatório de Correção

Todo relatório de bug corrigido deve seguir este formato mínimo:

```
Arquivo: <caminho>
Linha(s): <número>
Sintoma relatado: <o que o usuário observou>
Causa raiz confirmada: <o que o código realmente fazia, com trecho citado>
Correção aplicada: <diff ou trecho antes/depois>
Prova de funcionamento: <output real da execução pós-correção>
```

Relatórios que pulem o campo "Prova de funcionamento" são considerados incompletos
e não podem ser marcados como resolvidos.

