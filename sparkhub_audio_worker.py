import os
import time
import shutil
import hashlib
from pathlib import Path
import sparkhub_db

# Tentativa de importar o faster_whisper.
# Caso não esteja instalado, alerta o usuário graciosamente.
try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

STAGING_DIR = Path(os.path.join(os.path.dirname(__file__), "staging", "audio"))
ARCHIVE_DIR = Path(os.path.join(os.path.dirname(__file__), "staging", "processed", "audio"))

# Configuração do Modelo
# Usamos 'small' ou 'base' pois o SparkHub preza por baixo footprint e agilidade local.
MODEL_SIZE = "small"
COMPUTE_TYPE = "int8" # float16 se tiver GPU boa, int8 para CPU/GPU modesta.

def get_file_hash(filepath: Path) -> str:
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()

def process_audio_file(model, file_path: Path) -> int:
    print(f"[AUDIO WORKER] Transcrevendo: {file_path.name}")
    try:
        segments, info = model.transcribe(str(file_path), beam_size=5, language="pt")
        
        full_text = []
        for segment in segments:
            full_text.append(segment.text.strip())
            
        transcription = " ".join(full_text)
        
        if not transcription.strip():
            print(f"[AUDIO WORKER] Áudio sem fala reconhecível: {file_path.name}")
            return 0
            
        print(f"[AUDIO WORKER] Sucesso! Salvando no MemPalace...")
        content = f"Transcrição do arquivo de áudio '{file_path.name}':\n\n{transcription}"
        
        # Persiste nativamente no banco (wing: sensory, room: audio_transcription)
        mem_id = sparkhub_db.save_memory("sensory", "audio_transcription", content)
        
        return mem_id
    except Exception as e:
        print(f"[AUDIO WORKER] Falha ao processar {file_path.name}: {e}")
        return 0

def run_worker():
    print(f"=== SPARKHUB AUDIO WORKER (Faster Whisper) ===")
    
    if not WHISPER_AVAILABLE:
        print("[ERRO FATAL] faster-whisper não está instalado.")
        print("Para ativar a audição do SparkHub, execute: pip install faster-whisper")
        return
        
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    sparkhub_db.init_and_migrate_db()
    
    print(f"Carregando modelo local '{MODEL_SIZE}' (Isso pode levar alguns segundos na primeira vez)...")
    
    # device="auto" escolhe cuda se disponível, senão cai pro cpu.
    model = WhisperModel(MODEL_SIZE, device="auto", compute_type=COMPUTE_TYPE)
    print(f"[AUDIO WORKER] Operacional! Monitorando pasta: {STAGING_DIR}")
    
    supported_extensions = {".mp3", ".wav", ".m4a", ".ogg"}
    
    while True:
        try:
            for file_path in STAGING_DIR.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                    
                    # Deduplicação Baseada em Hash
                    file_hash = get_file_hash(file_path)
                    
                    if sparkhub_db.check_media_processed(file_hash):
                        print(f"[AUDIO WORKER] Arquivo duplicado ignorado (Hash já existe): {file_path.name}")
                        dest_path = ARCHIVE_DIR / file_path.name
                        if dest_path.exists():
                            dest_path = ARCHIVE_DIR / f"{int(time.time())}_{file_path.name}"
                        shutil.move(str(file_path), str(dest_path))
                        continue
                    
                    mem_id = process_audio_file(model, file_path)
                    
                    if mem_id > 0:
                        sparkhub_db.register_processed_media(file_hash, file_path.name, mem_id)
                        dest_path = ARCHIVE_DIR / file_path.name
                        if dest_path.exists():
                            dest_path = ARCHIVE_DIR / f"{int(time.time())}_{file_path.name}"
                            
                        print(f"  -> Arquivando em {dest_path}")
                        shutil.move(str(file_path), str(dest_path))
                    else:
                        print(f"  -> Falha. Áudio {file_path.name} não foi processado.")
                        
            time.sleep(3) # Ciclo de watchdog
        except Exception as e:
            print(f"[AUDIO WORKER] Erro no loop de watchdog: {e}")
            time.sleep(10)

if __name__ == "__main__":
    run_worker()
