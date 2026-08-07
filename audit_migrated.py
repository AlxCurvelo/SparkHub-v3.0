import sqlite3
from sparkhub_paths import get_path

TERMOS_SENSIVEIS = ["laudo", "perícia", "pericial", "confidencial", "rh", "contrato", "extrato", "sigiloso"]

def analyze_migrated_records():
    db_path = get_path("mempalace.db")
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Busca memórias sensíveis
    cursor.execute("SELECT id, wing, room FROM memories WHERE is_sensitive = 1 ORDER BY id ASC")
    rows = cursor.fetchall()
    
    results = []
    
    for row in rows:
        row_id = row["id"]
        wing = row["wing"]
        room = row["room"]
        
        room_lower = room.lower()
        wing_lower = wing.lower()
        
        motivos = []
        if "trabalho" in wing_lower or "trabalho" in room_lower:
            motivos.append("Regra de Origem (Workspace/Pasta de Trabalho)")
            
        for t in TERMOS_SENSIVEIS:
            if t in room_lower:
                motivos.append(f"Keyword '{t}' no Assunto/Título do Arquivo")
                
        if not motivos:
            motivos.append("Keyword encontrada (Falso Positivo: estava perdida no meio do texto, não no título)")
            
        results.append(f"ID #{row_id} | Origem: {wing} -> {room}")
        results.append(f"Motivo que ativou a criptografia: {', '.join(motivos)}")
        results.append("-" * 60)
        
    for r in results:
        print(r)

if __name__ == "__main__":
    analyze_migrated_records()
