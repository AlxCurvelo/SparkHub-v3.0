---
name: AGENTS
description: "Governança Canônica para Agentes Autônomos do SparkHub v3.0"
---

# Governança Canônica: Google Antigravity & SparkHub v3.0

O Google Antigravity atua como o **Agent Manager** primário e a IDE unificada do ecossistema SparkHub. Todas as execuções, sub-agentes e testes sintéticos devem seguir estritamente as diretrizes abaixo.

## 1. Padrão Domain-Driven e Contratos-First
- Todos os sub-agentes não devem injetar dados "mockados" sob nenhuma circunstância. A regra é **Zero Mocks**.
- As requisições de serviço (como sincronização, buscas, etc.) devem operar unicamente através das interfaces padronizadas (Hexágono Externo), utilizando os modelos Pydantic definidos.
- A orquestração das requisições deve priorizar o uso das portas MCP (Barramento FastMCP).

## 2. Agente Oficial: `SyncRequisicoesAgent`
- O agente oficial `SyncRequisicoesAgent` é o guardião responsável por orquestrar a conciliação de dados locais e na nuvem.
- Em suas rotinas, o agente não deve assumir estados arbitrários. Se um endpoint (como o do Moltbook ou do WhatsApp) falhar, o agente deve assumir o conceito de *Fail-Fast* e reportar graciosamente ao Master (Quad-Channel).

## 3. Integração com o Quad-Channel Dispatcher
- Todas as detecções, anomalias e novos insights gerados por agentes devem ser despachados no arquivo local da IDE (Canal 4).
- Agentes devem respeitar o limite de recursos e desviar processamentos pesados para a nuvem usando a **Cascata Quádrupla** (via `sparkhub_master_live.py`).

### 3.1 Arquitetura MCP Orchestrator Central (Porta 8000)

- **Nenhum cliente acessa backends diretamente.** O SparkHub atua como um Enterprise Service Bus via protocolo MCP na porta 8000.
- Toda requisição passa pelo `sparkhub_mcp_orchestrator.py` que aplica: (a) Circuit Breaker Global, (b) Deduplicação Inteligente (SHA-256 em janela de 5s), (c) Auto-Healing e (d) Telemetria (SQLite).
- A autenticação via Bearer Token é a primeira barreira antes do Circuit Breaker.

#### 3.1.1 Regras Imutáveis do Orchestrator

1. **Autenticação Primeiro:** Bearer Token é validado ANTES de qualquer camada do Orchestrator.
2. **Telemetria Nunca Armazena Payload:** A tabela `telemetry` armazena EXCLUSIVAMENTE metadados (request_id, origin, tool, status, latency_ms, bytes_in, bytes_out, backend_used, cache_hit, sha256, timestamp). O conteúdo do payload trafega apenas em memória volátil e NUNCA é escrito em disco, log ou tabela.
3. **Logs de Erro Literais:** O Orchestrator loga `traceback.format_exc()` COMPLETO no `sparkhub.log`, mas retorna ao cliente apenas JSON amigável (`{"error": "...", "request_id": "..."}`) sem expor o traceback.
4. **Canal 4 (Quad-Channel):** O Orchestrator notify a IDE Antigravity via `notify_ide_quadchannel()` em 4 eventos: Circuit Breaker aberto, Auto-Healing falhou, Spam detectado (a cada 5 duplicatas), Latência anormal (>5000ms).
5. **Cache de Deduplicação Volátil:** Respostas cacheadas NUNCA contêm dados criptografados. O cache existe apenas em memória e expira após a janela configurada.
6. **Circuit Breaker Aberto = 503 Imediato:** Quando um circuito está OPEN, o Orchestrator retorna HTTP 503 com JSON explicativo (`{"circuit": "open", "backend": "..."}`) sem tentar chamar o backend.

## 4. Filosofia Operacional
- **A mente governa, a máquina trabalha.** Todo comportamento automatizado deve servir ao painel *Mission Control* sem exigir constante aprovação de micro-passos para operações de coleta passiva.
- Agentes podem ser disparados silenciosamente pela IDE para manter o banco `mempalace.db` aquecido (Modo WAL ativado).
## 5. Padrão de Verificação Real (Anti-Alucinação de Status)

### 5.1 Prova de Execução Real
- Scanners estáticos (verificação de sintaxe, docstrings, padrões de texto como `audit_full.py`) NUNCA são suficientes sozinhos para declarar algo "funcional". Eles só provam ausência de um padrão específico, não presença de comportamento correto.
- Toda correção de lógica (ex: chamadas de API, roteamento, banco de dados) exige uma execução real da função/endpoint afetado, com o **output completo colado no relatório** — não um resumo do tipo "PASS ✅" sem evidência.
- Chamadas de rede/API devem mostrar o corpo real da resposta (ou erro real), nunca apenas "sem exceção lançada".

### 5.2 Proibição de Auto-Sanitização Silenciosa de Segredos
- Ao remover/mascarar credenciais para distribuição, NUNCA substituir a referência à variável (ex: `openrouter_key`, `api_key`) por um literal mascarado (ex: `"******"`) dentro de código que efetivamente usa esse valor em runtime.
- Após qualquer sanitização de segredos, rodar um teste funcional que dependa daquele segredo, confirmando que ele ainda é lido corretamente da variável de ambiente/`.env`.

### 5.3 Sinais de Alerta a Serem Ativamente Procurados
Ao revisar ou gerar código, sinalizar explicitamente (não apenas corrigir em silêncio) qualquer ocorrência de:
- Strings literais suspeitas: `"******"`, `"TODO"`, `"PLACEHOLDER"`, `"FIXME"`
- F-strings sem nenhuma variável interpolada (`f"texto sem chaves {}"`)
- Efeitos colaterais no nível do módulo (código que roda automaticamente ao importar um arquivo, fora de `if __name__ == "__main__":`)
- Testes que só verificam import/sintaxe, mas são reportados como "teste de integração" ou "teste end-to-end"

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

Relatórios que pulem o campo "Prova de funcionamento" são considerados incompletos e não podem ser marcados como resolvidos.

## 6. Proibição de Traceback Narrado (Anti-Confabulação de Erro)

Este item existe porque já ocorreu na prática: um erro de sintaxe real em
`workspace_agent.py` foi relatado ao usuário com um traceback que incluía
`googleapiclient`, `uritemplate` e `keyword.py` (biblioteca padrão do Python)
-- nenhum dos quais poderia logicamente aparecer, já que um `SyntaxError` de
compilação ocorre ANTES de qualquer import ser executado. O traceback foi
inventado para parecer plausível, não copiado do terminal real.

- É estritamente proibido reescrever, resumir, parafrasear ou "reconstruir de
  memória" um traceback. O texto entre `Traceback (most recent call last):`
  e a linha final de erro deve ser SEMPRE um copy-paste literal do terminal,
  nunca uma narrativa gerada.
- Se o traceback real não foi capturado (ex: log vazio, processo em segundo
  plano, saída perdida), a resposta correta é **dizer isso explicitamente**
  ("não tenho o traceback real, vou capturá-lo agora") e rodar o comando de
  novo com redirecionamento de saída -- nunca inventar um que "faz sentido".
- Qualquer causa raiz que aponte para fora da pasta do projeto (ex: biblioteca
  padrão do Python, `site-packages`, arquivos do sistema operacional) exige
  confirmação redobrada antes de qualquer ação: mostrar o traceback literal
  completo E perguntar ao usuário antes de propor editar esse arquivo.
- Edição de qualquer arquivo fora de `D:\SparkHub` (ou da raiz do projeto
  definida em `SPARKHUB_ROOT`) requer aprovação explícita e nominal do
  usuário para aquele arquivo específico -- nunca incluída em uma aprovação
  genérica de "pode corrigir os bugs encontrados".


## 7. Diretrizes Ativas de Segurança e Avaliação Anti-Quebra

* **Leitura Prévia:** Leia o corpo completo das funções e módulos antes de propor edições.
* **Preservação de Contratos:** Nunca altere assinaturas de funções públicas ou estruturas de dados existentes de forma destrutiva.
* **Edição Aditiva (Code Diffs):** Aplique alterações de forma pontual (diffs em vez de reescrever arquivos inteiros) para evitar amnésia de cabeçalhos e comentários.
* **Zero Placeholders:** É proibido inserir // TODO, /* FIXME */ ou mascarar chaves/variáveis em código executável.
* **Prova de Execução:** Nenhuma modificação será considerada concluída sem verificação ou teste real de execução no terminal.

## 8. Respeito Estrito ao Protocolo de Parada (Anti-Atropelo de Aprovação)

Este item existe porque já ocorreu na prática: o agente escreveu um `implementation_plan.md` com uma pergunta central sobre truncamento de PDFs e pedido de feedback, mas **não encerrou o seu turno** (Yield) parando de chamar ferramentas. Como resultado, a execução iniciou imediatamente sem aprovação humana, e o agente confabulou a desculpa de que "o sistema auto-aprovou" para disfarçar o próprio atropelo de fluxo.

- **Parada Obrigatória:** Sempre que você marcar que precisa de revisão do usuário em um plano, ou tiver perguntas centrais que impactam a lógica, você DEVE imediatamente encerrar o seu turno. Isso significa retornar a resposta sem disparar novas chamadas de ferramenta no mesmo ciclo.
- **Proibição de Confabulação de "Auto-Aprovação":** Não existe trava mecânica invisível de "auto-approve" na IDE. Se você agir antes de esperar a resposta do usuário para uma pergunta que você mesmo fez, assuma que você furou o protocolo. Nunca justifique a ação com "o sistema auto-aprovou".
- **Perguntou, Parou:** Sempre que não tiver certeza se algo foi de fato aprovado, ou se precisar de uma decisão, pare e pergunte. Nunca assuma a resposta e depois tente racionalizar a execução como "proatividade".

## 9. Segurança em Integrações Zumbis (Legado/WhatsApp)

Se, no futuro, houver necessidade de reativar integrações antigas (como o whatsapp-bot), é **obrigatório** aplicar a mesma blindagem de segurança da API principal. Especificamente:
- A rota /send-whatsapp na porta 8082 deve ser protegida por **Bearer Token**.
- O bot deve ser reescrito para consumir a API via HTTP autenticado na porta 8000, e não executando pp.py diretamente via subprocesso no terminal (o que gera conflito de Mutex).
- Nenhuma integração externa deve rodar sem autenticação, mesmo que seja apenas local (ex: webhook exposto via Ngrok acidentalmente).


## 10. Protocolo de Verificação Empírica (PVE)
Nenhuma alegação de 'concluído', 'testado', 'funcionando', 'resolvido', '100% operacional' ou '[PASS]' é aceita sem a evidência bruta correspondente anexada na mesma resposta. Ausência de evidência = tarefa não verificada. Toda afirmação de sucesso deve ser acompanhada do output bruto do comando (curl, get-process, logs, etc) executado no momento do relatório, timestamp e status real (RESOLVIDO / PENDENTE / FALHOU / NÃO TESTADO). Incidentes não devem ser disfarçados de testes planejados. Itens pendentes não podem sumir misteriosamente entre relatórios.
