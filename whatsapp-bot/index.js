const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const qrcodeImg = require('qrcode');
const express = require('express');
const { exec } = require('child_process');
const path = require('path');
const os = require('os');

const app = express();
app.use(express.json());

// Configuração Antifrágil do Puppeteer
const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        headless: true,
        executablePath: process.env.PUPPETEER_EXECUTABLE || 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox'
        ]
    }
});

client.on('qr', (qr) => {
    console.log('\n======================================================');
    console.log('[SPARKHUB] Escaneie o QR Code abaixo com seu WhatsApp:');
    console.log('======================================================\n');
    qrcode.generate(qr, { small: true });
    
    // Gerar a imagem real e salvar na pasta de artefatos
    const artifactPath = process.env.WHATSAPP_QR_PATH || path.resolve(os.homedir(), '.gemini', 'antigravity', 'brain', 'whatsapp_qr.png');
    qrcodeImg.toFile(artifactPath, qr, {
        color: {
            dark: '#000000',  // Black dots
            light: '#FFFFFF' // White background
        }
    }, function (err) {
        if (err) throw err;
        console.log('[SPARKHUB] Imagem do QR Code salva com sucesso em:', artifactPath);
    });
});

client.on('ready', () => {
    console.log('🟢 WhatsApp Client is READY!');
});

// Listener antifrágil para comandos e ChatOps via WhatsApp
client.on('message_create', async msg => {
    // Ignora mensagens enviadas que sejam respostas do próprio bot para evitar loop infinito
    if (msg.body && (msg.body.includes('🚀') || msg.body.includes('🤖'))) return;

    const text = (msg.body || '').trim();
    const textLower = text.toLowerCase();
    
    // Ignora se for mensagem vazia
    if (!text) return;

    if (textLower === '!ping') {
        msg.reply('🚀 Pong Antifrágil! Comunicação estabelecida.');
        return;
    }

    // (Opcional) Mantém o atalho rápido antigo apenas para o chat de anotações ("Você")
    // Se a mensagem for "!sync" exato, roda a sincronização rápida e encerra.
    if (textLower === '!sync') {
        await msg.reply('🤖 SparkHub: Executando sincronização de requisições...');
        exec(`python "${path.resolve(__dirname, '..', 'sync_requisicoes_master.py')}" --scope=sheets`, (error, stdout, stderr) => {
            msg.reply(stdout ? `🤖 Concluído:\n${stdout.trim().slice(-500)}` : `⚠️ Erro: ${error && error.message}`);
        });
        return;
    }

    // TRAVA DE SEGURANÇA ANTIFRÁGIL: Só aciona a IA se a mensagem começar com "!"
    // Isso evita que o SparkHub responda acidentalmente a mensagens da sua família ou grupos de trabalho!
    if (textLower.startsWith('!')) {
        // Remove o "!" inicial para passar limpo para a IA
        let query = text.substring(1).trim();
        // Caso o usuário tenha digitado "! ai", "!bot", etc, limpamos isso também
        if (query.toLowerCase().startsWith('ai ')) query = query.substring(3).trim();
        if (query.toLowerCase().startsWith('bot ')) query = query.substring(4).trim();
        
        console.log(`[WHATSAPP BOT] Comando Roteador IA recebido: "${query}"`);
        
        await msg.reply('🤖 SparkHub: Processando sua requisição com a IA...');
        
        // Protege contra escape de aspas no terminal do Windows
        const safeQuery = query.replace(/"/g, '\\"');
        const pythonCmd = `python "${path.resolve(__dirname, '..', 'app.py')}" ask_ai "${safeQuery}" --profile=cloud`;

        exec(pythonCmd, { timeout: 60000 }, (error, stdout, stderr) => {
            let replyText = '🤖 SparkHub:\n\n';
            if (stdout) {
                // Divisão cirúrgica: remove os logs de inicialização e [AUTO-DISCOVERY] do Python
                const parts = stdout.split('=== RESULTADO ===');
                if (parts.length > 1) {
                    replyText += parts[parts.length - 1].trim();
                } else {
                    replyText += stdout.trim();
                }
                
                // Limpeza opcional das tags internas de roteamento (ex: [🚀 VRAM_FAST: Localhost])
                replyText = replyText.replace(/\[☁️ CLOUD_PROXY: OpenRouter\]\n/g, '');
                replyText = replyText.replace(/\[☁️ CLOUD_PROXY: Gemini\]\n/g, '');
                replyText = replyText.replace(/\[🚀 VRAM_FAST: Localhost\]\n/g, '');
                replyText = replyText.replace(/\[🧠 FALLBACK LOCAL: Ollama\]\n/g, '');
                
            } else if (stderr) {
                replyText += `⚠️ Aviso: ${stderr.trim()}`;
            }
            if (error) {
                replyText += `\n❌ Erro de processamento: ${error.message}`;
            }

            msg.reply(replyText.trim());
        });
        
        return;
    }
});

client.on('disconnected', (reason) => {
    console.log('🔴 WhatsApp Client was DISCONNECTED. Reason:', reason);
    console.log('Tentando reconectar...');
    client.initialize();
});

// Inicializa a escuta no WhatsApp
client.initialize();

// Configura o Express Gateway na porta 8082
app.post('/send-whatsapp', async (req, res) => {
    // 1. Resposta Fire-and-Forget extremamente rapida (<100ms)
    res.json({ status: "processing" });

    // 2. Tenta enviar no background assíncrono
    try {
        const { phone, message } = req.body;
        if (!phone || !message) {
            console.log('[WHATSAPP] Falta telefone ou mensagem.');
            return;
        }

        // Verifica status da conexão antes de enviar
        const state = await client.getState();
        if (state !== 'CONNECTED') {
            console.log(`[WHATSAPP ERROR] Cliente não conectado (Estado: ${state}). Ignorando envio para ${phone}.`);
            return;
        }

        // Se o número de destino for o mesmo número do bot, envia para a conversa "Você" (Anotações)
        let finalChatId = `${phone}@c.us`;
        const myNumber = client.info.wid.user; 
        
        // Verifica se o telefone pedido contém o nosso próprio número (ignorando o 9º dígito se necessário)
        if (myNumber.includes(phone.slice(4)) || phone.includes(myNumber.slice(4))) {
            finalChatId = client.info.wid._serialized;
        }

        await client.sendMessage(finalChatId, message);
        console.log(`[WHATSAPP ENVIADO] Mensagem encaminhada para: ${finalChatId}`);
    } catch (err) {
        console.log('[WHATSAPP ERROR] Falha no envio assíncrono:', err.message);
    }
});

// Health Check para acesso via navegador (Celular via Tailscale)
app.get('/', (req, res) => {
    res.send(`
        <html>
            <body style="background-color: #1a1a1a; color: #00ff00; font-family: monospace; padding: 50px; text-align: center;">
                <h1>🟢 SparkHub WhatsApp Gateway</h1>
                <h2>Status: ATIVO E OPERACIONAL</h2>
                <p>Este nó está rodando de forma antifrágil no seu PC.</p>
                <p>Você acessou via Tailscale VPN! 🚀</p>
            </body>
        </html>
    `);
});

const PORT = 8082;
app.listen(PORT, () => {
    console.log(`🚀 Gateway Node.js rodando em http://localhost:${PORT}/send-whatsapp`);
});
