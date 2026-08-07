import os
import time
import shutil
import base64
import json
import urllib.request
import mimetypes
import hashlib
from pathlib import Path
from dotenv import load_dotenv
import sparkhub_db

load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
STAGING_DIR = Path(os.path.join(os.path.dirname(__file__), "staging", "vision"))
ARCHIVE_DIR = Path(os.path.join(os.path.dirname(__file__), "staging", "processed", "vision"))

VISION_PROMPT = (
    "Você é o módulo visual do SparkHub v3.0. "
    "Descreva detalhadamente o que há nesta imagem ou frame de vídeo. "
    "Se houver textos (OCR), transcreva-os literalmente. "
    "Se for uma interface gráfica, explique a função provável da tela. "
    "Seja denso, técnico e objetivo, pois o seu relatório alimentará uma memória vetorial de longo prazo."
)

def get_file_hash(filepath: Path) -> str:
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()

def encode_image(file_path: Path):
    with open(file_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def analyze_vision_media(file_path: Path) -> int:
    if not GEMINI_API_KEY or GEMINI_API_KEY == "sua_chave_google_ai_studio_aqui":
        print("[VISION WORKER] ERRO: Chave GEMINI_API_KEY inválida no .env")
        return 0
        
    print(f"[VISION WORKER] Analisando: {file_path.name}")
    
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type or not mime_type.startswith("image/"):
        print(f"[VISION WORKER] Tipo MIME não suportado para {file_path.name}")
        return 0

    base64_data = encode_image(file_path)
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    
    payload = {
        "contents": [{
            "parts": [
                {"text": VISION_PROMPT},
                {
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": base64_data
                    }
                }
            ]
        }]
    }
    
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method='POST')
        with urllib.request.urlopen(req, timeout=45) as response:
            res_json = json.loads(response.read().decode('utf-8'))
            text = res_json.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            
            if text:
                print(f"[VISION WORKER] Sucesso! Gravando extração no MemPalace...")
                content = f"Análise Visual do arquivo '{file_path.name}':\n\n{text}"
                mem_id = sparkhub_db.save_memory("sensory", "vision_analysis", content)
                return mem_id
                
        return 0
    except Exception as e:
        print(f"[VISION WORKER] Erro na API do Gemini: {e}")
        return 0

def run_worker():
    print(f"=== SPARKHUB VISION WORKER (Gemini 2.0 Flash) ===")
    
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    sparkhub_db.init_and_migrate_db()
    
    print(f"[VISION WORKER] Operacional! Monitorando pasta: {STAGING_DIR}")
    
    supported_extensions = {".jpg", ".jpeg", ".png", ".webp"}
    
    while True:
        try:
            for file_path in STAGING_DIR.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                    
                    file_hash = get_file_hash(file_path)
                    if sparkhub_db.check_media_processed(file_hash):
                        print(f"[VISION WORKER] Arquivo duplicado ignorado (Hash já existe): {file_path.name}")
                        dest_path = ARCHIVE_DIR / file_path.name
                        if dest_path.exists():
                            dest_path = ARCHIVE_DIR / f"{int(time.time())}_{file_path.name}"
                        shutil.move(str(file_path), str(dest_path))
                        continue
                        
                    mem_id = analyze_vision_media(file_path)
                    
                    if mem_id > 0:
                        sparkhub_db.register_processed_media(file_hash, file_path.name, mem_id)
                        dest_path = ARCHIVE_DIR / file_path.name
                        if dest_path.exists():
                            dest_path = ARCHIVE_DIR / f"{int(time.time())}_{file_path.name}"
                        
                        print(f"  -> Arquivando imagem processada em {dest_path}")
                        shutil.move(str(file_path), str(dest_path))
                    else:
                        print(f"  -> Falha. Tentará novamente no próximo ciclo se aplicável.")
                        pass
                        
            time.sleep(3) # Watchdog veloz
        except Exception as e:
            print(f"[VISION WORKER] Erro fatal no loop: {e}")
            time.sleep(10)

if __name__ == "__main__":
    run_worker()
