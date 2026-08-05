""" SparkHub v3.0 - Script de Povoamento do MemPalace """
import sqlite3
from datetime import datetime, timezone
from sparkhub_paths import get_path

MEMORIES = [
    # 1. WING: Profile (Perfil Pessoal, Família e Formação)
    ("Profile", "personal", "Nome oficial: Alexandre Cavalcante Curvelo. Apelidos e nomes curtos: Ale ou Curvelo."),
    ("Profile", "personal", "Residência e Localização: Embu-Guaçu, São Paulo, Brasil. Fuso Horário: America/Sao_Paulo (UTC-3)."),
    ("Profile", "family", "Família: Casado com Karina Curvelo. Tem duas filhas adultas chamadas Ágape e Sofia."),
    ("Profile", "education", "Formação e Educação: Graduado em Educação Artística / Artes Plásticas. Cursando Análise e Desenvolvimento de Sistemas."),
    ("Profile", "career", "Áreas de Atuação: Designer gráfico, ilustrador, modelador 3D e desenvolvedor de software/jogos freelance."),
    # 2. WING: System (Regras do SO e Recursos do SparkHub)
    ("System", "hardware", "Instalação Principal: Windows 11 no diretório base D:\\SparkHub."),
    ("System", "hardware", "Regra de Hardware GPU/VRAM: Placa de vídeo compartilhada entre jogos (Godot 4), renderização (Blender) e live (OBS)."),
    ("System", "router", "Regra do Roteador Multi-Mode: Usar Ollama local (VRAM_FAST com Speculative Decoding) quando o PC estiver livre. Desviar 100% para Cloud Proxy gratuito (OpenRouter / Gemini Flash REST API) quando houver softwares pesados abertos ou em caso de erro 10061."),
    ("System", "security", "Regra do Disk Guard: Verificar se o volume D:\\ tem mais de 50 MB livres antes de qualquer download ou ingestão."),
    # 3. WING: Projects (Projetos de Jogos - Jubileu & Neon Orbit 360)
    ("Projects", "jubileu", "Projeto Jubileu Steampunk: Personagem interativo corvo antropomórfico estilo steampunk para live no TikTok Studio."),
    ("Projects", "jubileu", "Jubileu - Personalidade e Design: Sarcástico, zombeteiro e bem-humorado. Acessórios: boina italiana clássica, monóculo, engrenagens de latão e fraque marrom."),
    ("Projects", "jubileu", "Jubileu - 10 Expressões Corporais: 1. Confiante/Orgulhoso, 2. Curioso/Inspecionando, 3. Assustado, 4. Bravo/Confrontacional, 5. Brincalhão/Travesso, 6. Abatido, 7. Rindo, 8. Pensativo, 9. Aliviado (suspiro de vapor), 10. Exausto/Colapsado."),
    ("Projects", "jubileu", "Jubileu - Fases do Projeto: Fase 1 MVP (vídeos pré-renderizados acionados em live); Fase 2 (Integração local Ollama para responder chat em tempo real); Fase 3 (Sensibilidade áudio multicanal e tradução de diálogos de jogos)."),
    ("Projects", "neon_orbit", "Projeto GDD Neon Orbit 360: Jogo de ação/puzzle 360 graus de precisão física na Godot 4. Player baseado em RigidBody2D com gravidade de nós de órbita."),
    ("Projects", "antigravity", "Integração Godot MCP Server: Servidor WebSocket de sincronização direta entre a IDE Google Antigravity e a árvore de cenas (.tscn) da Godot Engine 4."),
    # 4. WING: Business (Projetos Comerciais & Empreendedorismo)
    ("Business", "delika", "Projeto Deliká Bolos e Doces: Marca de confeitaria da família. Contabilidade de produtos, margens de ingredientes e material promocional em vídeo."),
    ("Business", "mary_kay", "Projeto Mary Kay: Consultoria gerenciada por Karina Curvelo. Produção de materiais de marketing digital e catálogo de produtos."),
    ("Business", "tiktok_shop", "Projeto TikTok Shop: Ativação de loja e central de vendedor digital para e-commerce."),
    # 5. WING: Skills (Competências de Software & Tecnologias)
    ("Skills", "design", "Softwares de Design e 2D: Experiência avançada em CorelDRAW (substituindo Illustrator), Photoshop e Sketchbook Pro."),
    ("Skills", "3d", "Softwares de 3D e Animação: Blender e 3ds Max para modelagem de assets, rigging e animação."),
    ("Skills", "dev", "Linguagens e Motores: GDScript (Godot 4), Python 3.12, HTML5, CSS3, JavaScript / Node.js."),
    ("Skills", "sparkhub", "Infraestrutura de Automação SparkHub: Servidor MCP em background, CLI spark, SQLite com modo WAL, WhatsApp Bot (whatsapp-web.js porta 8082), Discord Webhook e Tailscale VPN Mesh.")
]

def seed_mempalace(db_path: str = None):
    if db_path is None:
        db_path = str(get_path("mempalace.db"))
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wing TEXT NOT NULL,
            room TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL
        );
    """)
    now_iso = datetime.now(timezone.utc).isoformat()
    inserted_count = 0
    for wing, room, content in MEMORIES:
        cur.execute("SELECT id FROM memories WHERE content = ?;", (content,))
        if not cur.fetchone():
            cur.execute("""
                INSERT INTO memories (wing, room, content, timestamp)
                VALUES (?, ?, ?, ?);
            """, (wing, room, content, now_iso))
            inserted_count += 1
    conn.commit()
    conn.close()
    print(f"[MEMPALACE SEED SUCCESS] {inserted_count} memórias de perfil, hardware e projetos inseridas em '{db_path}'!")

if __name__ == "__main__":
    seed_mempalace()
