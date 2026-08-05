# 🚀 Manual do Usuário: SparkHub v3.0 (Edição Descentralizada)

Bem-vindo ao **SparkHub v3.0**, um orquestrador local autônomo, antifrágil e de custo zero (R$ 0,00) para automação e inteligência artificial.

## 🛠️ Requisitos do Sistema
- Sistema Operacional: Windows 11 (64-bits)
- Interpretador Python 3.12+ instalado na máquina.

---

## ⚙️ Passo a Passo da Instalação

### 1. Configuração das Chaves de Acessos Gratuitos (Tríplice Cascata)
Para que o SparkHub processe IA sem custos, você precisará de chaves gratuitas próprias:
- **OpenRouter Free:** Acesse [openrouter.ai/keys](https://openrouter.ai/keys) para criar sua conta gratuita e gerar sua chave.
- **Google AI Studio (Gemini):** Acesse [aistudio.google.com](https://aistudio.google.com/) para obter sua chave de API do Gemini.

### 2. Executando o Instalador Interativo
1. Abra o terminal na pasta do SparkHub.
2. Execute o instalador interativo:
   ```cmd
   python setup_staging_quadchannel.py
   ```
3. O script guiará você na inserção das suas chaves, gerando automaticamente o arquivo `.env` de configuração, criando o banco de dados local (`mempalace.db`) virgem e estruturando a pasta de *staging*.

### 3. Ativando a Inicialização Automática (Daemon Boot)

Para que o sistema suba de forma oculta e autônoma junto com o Windows 11:

* Clique com o botão direito no arquivo `install_daemon.bat` e selecione **Executar como Administrador**.

---

## 🛡️ Segurança e Sandbox (Moltbook & Ingestão Externa)

O ecossistema utiliza uma **Zona de Staging** para ingestão estritamente passiva (dados lidos como texto bruto). Isso blinda o seu computador contra qualquer tentativa de *prompt injection* externo, garantindo um fluxo seguro com validação humana (*Human-in-the-Loop*).
