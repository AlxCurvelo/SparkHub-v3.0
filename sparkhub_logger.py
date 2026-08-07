import logging
import os
from logging.handlers import RotatingFileHandler
from sparkhub_paths import get_path

# Garantir que a pasta de logs exista
LOGS_DIR = get_path("logs")
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOGS_DIR, "sparkhub.log")

def setup_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Evita duplicação se já estiver configurado
    if not logger.handlers:
        # Handler para o arquivo rotativo (máximo 5MB, mantém até 3 backups)
        file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding='utf-8')
        file_handler.setLevel(logging.INFO)

        # Handler para o console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Formato (preserva espaço para as tags existentes como [SECURITY], [ROTEADOR WARN])
        formatter = logging.Formatter('%(asctime)s | %(levelname)-7s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger

# Instância padrão para uso geral
logger = setup_logger("sparkhub")
