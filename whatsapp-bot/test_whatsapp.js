const { Client, LocalAuth } = require('whatsapp-web.js');

const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        executablePath: "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    }
});

client.on('ready', async () => {
    console.log('🟢 WhatsApp Client is READY!');
    const phone = "5511995532053";
    
    // Test 1: getNumberId
    const numberId = await client.getNumberId(phone);
    console.log('getNumberId result:', numberId);
    
    // Test 2: Send to @c.us with 9th digit
    try {
        await client.sendMessage(phone + "@c.us", "🚀 [Teste de Diagnóstico Antifrágil] Mensagem direta (Com 9o Dígito)");
        console.log("Enviado para " + phone + "@c.us");
    } catch (e) {
        console.log("Erro no 9o digito:", e.message);
    }

    // Test 3: Send to @c.us without 9th digit
    const phoneSemNove = "551195532053";
    try {
        await client.sendMessage(phoneSemNove + "@c.us", "🚀 [Teste de Diagnóstico Antifrágil] Mensagem direta (Sem 9o Dígito)");
        console.log("Enviado para " + phoneSemNove + "@c.us");
    } catch (e) {
        console.log("Erro sem 9o digito:", e.message);
    }

    console.log("Teste finalizado. Saindo...");
    process.exit(0);
});

client.initialize();
