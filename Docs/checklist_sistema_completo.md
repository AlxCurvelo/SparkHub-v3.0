# Plano de Homologação Completo - SparkHub v3.0

Esta é a bateria de testes *End-to-End* (Ponta a Ponta) para auditar toda a arquitetura do SparkHub v3.0. Marque os itens à medida que for validando cada subsistema.

## 1. Subsistema de Orquestração (Startup & Widget)
> [!IMPORTANT]
> Garante que o motor de inicialização e a interface de bandeja (Systray) estejam blindados e respondam corretamente.

- [ ] **Startup a Frio:** Execute o `iniciar_sparkhub.bat`. O sistema não deve apresentar erros fatais e o ícone verde deve surgir na bandeja do sistema (canto direito inferior).
- [ ] **Blindagem de Instância:** Com o widget aberto, execute o atalho de inicialização mais 2 vezes. Nenhuma nova janela/ícone deve aparecer. O sistema rejeitará duplicações.
- [ ] **Navegação do Menu:** Clique com o botão direito no widget e valide as cores e funcionalidades:
    - [ ] `🌐 Abrir Dashboard`: Abre a interface no Edge. Ao clicar de novo, traz a aba existente para frente.
    - [ ] `⚡ Terminal PowerShell`: Abre um terminal azul apontando para `D:\SparkHub`.
    - [ ] `Sinalizações`: Ao clicar em "Processando", o ícone e a borda devem ficar amarelos; "Offline" vermelhos; "Operacional" volta para verde.
- [ ] **Auto-Healing (Tolerância a Falhas):** Feche a janela de console do "SparkHub API" ou mate os processos do Python via Task Manager. Clique em `Abrir Dashboard`. O widget deve religar a API silenciosamente antes de abrir a janela.

## 2. Subsistema de Interface (Dashboard)
> [!TIP]
> Valida se a interface web de painel de controle está responsiva e recebendo dados corretamente da porta 8085.

- [ ] **Acesso:** Abra `http://127.0.0.1:8085` no Edge (via widget). O painel dark mode GDD-as-Code deve carregar imediatamente.
- [ ] **Card 01 - Saúde do Armazenamento:** Verifique se o espaço em disco do `C:\` está sendo lido corretamente com o status (ex: NORMAL).
- [ ] **Card 02 - Memória MemPalace:** O card deve exibir o "Total" de memórias cadastradas no banco de dados SQLite (`mempalace.db`) e o resumo por pastas/módulos.
- [ ] **Formulário de Comando:** Digite "teste de input" no campo de comando inferior e pressione Enviar. (Atualmente configurado para alertar no console ou processar; valide se o layout não quebra ao enviar).
- [ ] **Layout Responsivo:** Redimensione a janela do Edge do formato paisagem para o formato "celular" (estreito). Os cards devem se adaptar fluidamente.

## 3. Subsistema Core & Integrações (API e Ngrok)
> [!CAUTION]
> Testa o motor principal da aplicação (Porta 8000), o redirecionamento externo e o banco de dados.

- [ ] **Healthcheck Local:** Abra `http://127.0.0.1:8000/api/health` ou `/`. Deve retornar um JSON com `status: ok` ou tela de boas-vindas da API.
- [ ] **Acesso Externo (Ngrok):** O console do Ngrok deve estar rodando em segundo plano apontando para `siesta-usage-cannabis.ngrok-free.dev`. Se você acessar essa URL pelo celular, ela deve chegar na sua API Core.
- [ ] **Banco de Dados (WAL):** Utilizando o DBeaver ou script, abra `mempalace.db`. Valide se o modo WAL (Write-Ahead Logging) está ativado, evitando o bloqueio da base de dados se múltiplos agentes tentarem ler/escrever ao mesmo tempo.

## 4. Subsistema de Inteligência (Router AI)
> [!NOTE]
> Valida se os módulos de roteamento estão estruturalmente prontos para receber o tráfego do Master Agent.

- [ ] **Verificação de Importação:** Na janela de console da API (onde o `app.py` roda), confira se há alguma mensagem de "SyntaxError" ou falha ao carregar o `router_ai.py`.
- [ ] **Quad-Channel Dispatcher:** Verifique se os logs locais da IDE do Antigravity (Canal 4) e o `notifications.json` estão sendo lidos/escritos corretamente sem conflitos de permissão de pasta.

---
**Instruções de Reporte:**
Realize a varredura completa. Se qualquer caixa não puder ser marcada, reporte-me a etapa exata e o erro que apareceu na tela. Se 100% estiver verde, o sistema está **Production Ready**.
