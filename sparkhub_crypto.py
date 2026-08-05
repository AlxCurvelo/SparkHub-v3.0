"""
SparkHub v3.0 - Módulo de Criptografia Simétrica de Dados Sensíveis
Localização: D:\\SparkHub\\sparkhub_crypto.py
"""

import os
from cryptography.fernet import Fernet

from sparkhub_paths import get_path

class SparkHubCrypto:
    """Gerenciador de Criptografia Simétrica para o MemPalace."""
    def __init__(self, key_path: str | None = None):
        self.key_path = key_path or str(get_path(".master_key"))
        self.fernet = Fernet(self._get_or_create_key())

    def _get_or_create_key(self) -> bytes:
        if os.path.exists(self.key_path):
            with open(self.key_path, "rb") as f:
                return f.read().strip()
        else:
            new_key = Fernet.generate_key()
            os.makedirs(os.path.dirname(self.key_path), exist_ok=True)
            with open(self.key_path, "wb") as f:
                f.write(new_key)
            return new_key

    def encrypt_text(self, plain_text: str) -> str:
        cipher_bytes = self.fernet.encrypt(plain_text.encode("utf-8"))
        return f"[ENCRYPTED]:{cipher_bytes.decode('utf-8')}"

    def decrypt_text(self, cipher_text: str) -> str:
        if not cipher_text.startswith("[ENCRYPTED]:"):
            return cipher_text
        raw_cipher = cipher_text.replace("[ENCRYPTED]:", "").encode("utf-8")
        return self.fernet.decrypt(raw_cipher).decode("utf-8")
