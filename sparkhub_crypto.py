import os
import pyotp
import qrcode
import ctypes
import ctypes.wintypes
from cryptography.fernet import Fernet
import winreg
from sparkhub_paths import get_path
from dotenv import load_dotenv, set_key

class LockedException(Exception):
    pass

class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", ctypes.wintypes.DWORD),
                ("pbData", ctypes.c_void_p)]

ctypes.windll.kernel32.LocalFree.argtypes = [ctypes.c_void_p]
ctypes.windll.kernel32.LocalFree.restype = ctypes.c_void_p

def _get_machine_guid() -> str:
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as key:
            val, _ = winreg.QueryValueEx(key, "MachineGuid")
            return val
    except Exception:
        return "fallback-machine-guid"

def dpapi_encrypt(data: bytes, entropy: bytes = None) -> bytes:
    crypt32 = ctypes.windll.crypt32
    
    blob_in = DATA_BLOB(len(data), ctypes.cast(ctypes.c_char_p(data), ctypes.c_void_p).value)
    
    p_entropy = None
    if entropy:
        blob_entropy = DATA_BLOB(len(entropy), ctypes.cast(ctypes.c_char_p(entropy), ctypes.c_void_p).value)
        p_entropy = ctypes.byref(blob_entropy)
        
    blob_out = DATA_BLOB()
    
    # CRYPTPROTECT_UI_FORBIDDEN = 0x1
    if crypt32.CryptProtectData(ctypes.byref(blob_in), None, p_entropy, None, None, 1, ctypes.byref(blob_out)):
        res = ctypes.string_at(blob_out.pbData, blob_out.cbData)
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)
        return res
    raise RuntimeError("Failed to encrypt with DPAPI")

def dpapi_decrypt(data: bytes, entropy: bytes = None) -> bytes:
    crypt32 = ctypes.windll.crypt32
    
    blob_in = DATA_BLOB(len(data), ctypes.cast(ctypes.c_char_p(data), ctypes.c_void_p).value)
    
    p_entropy = None
    if entropy:
        blob_entropy = DATA_BLOB(len(entropy), ctypes.cast(ctypes.c_char_p(entropy), ctypes.c_void_p).value)
        p_entropy = ctypes.byref(blob_entropy)
        
    blob_out = DATA_BLOB()
    
    if crypt32.CryptUnprotectData(ctypes.byref(blob_in), None, p_entropy, None, None, 1, ctypes.byref(blob_out)):
        res = ctypes.string_at(blob_out.pbData, blob_out.cbData)
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)
        return res
    raise RuntimeError("Failed to decrypt with DPAPI")

def get_totp_secret() -> str:
    env_path = get_path(".env")
    load_dotenv(env_path)
    secret = os.environ.get("TOTP_SECRET")
    
    if not secret:
        secret = pyotp.random_base32()
        set_key(env_path, "TOTP_SECRET", secret)
        os.environ["TOTP_SECRET"] = secret
        
        # Generates QR Code for Authenticator
        uri = pyotp.totp.TOTP(secret).provisioning_uri(name="SparkHub", issuer_name="Antigravity")
        img = qrcode.make(uri)
        img.save(get_path("whatsapp_qr_totp.png"))
        print("[CRIPTO] NOVO SEGREDO TOTP GERADO! Escaneie whatsapp_qr_totp.png no Google Authenticator.")
        
    return secret

def check_rate_limit() -> bool:
    lock_file = get_path(".totp_lockout")
    import time
    
    if os.path.exists(lock_file):
        with open(lock_file, "r") as f:
            data = f.read().strip().split(",")
            if len(data) == 2:
                attempts, last_fail = int(data[0]), float(data[1])
                # 15 minutes = 900 seconds
                if attempts >= 5 and (time.time() - last_fail) < 900:
                    return False
                if (time.time() - last_fail) >= 900:
                    # Reset if 15 mins passed
                    os.remove(lock_file)
    return True

def record_failed_attempt():
    lock_file = get_path(".totp_lockout")
    import time
    attempts = 0
    if os.path.exists(lock_file):
        with open(lock_file, "r") as f:
            data = f.read().strip().split(",")
            if len(data) == 2:
                attempts = int(data[0])
    
    attempts += 1
    with open(lock_file, "w") as f:
        f.write(f"{attempts},{time.time()}")
    print(f"[SECURITY] Falha no TOTP registrada. Tentativa {attempts}/5.")
    
def clear_failed_attempts():
    lock_file = get_path(".totp_lockout")
    if os.path.exists(lock_file):
        os.remove(lock_file)

def unlock_vault(totp_code: str) -> bool:
    if not check_rate_limit():
        print("[SECURITY] Bloqueio de Rate Limit ativo (máx 5 tentativas). Aguarde 15 minutos.")
        raise LockedException("Muitas tentativas falhas. Cofre temporariamente bloqueado por 15 minutos.")
        
    secret = get_totp_secret()
    totp = pyotp.TOTP(secret)
    if totp.verify(totp_code):
        clear_failed_attempts()
        
        # Evita sobrescrever se a chave atual for válida e decriptável
        try:
            get_aes_key()
            return True # Já está destrancado com uma chave válida
        except Exception:
            pass # Continua e gera nova chave
            
        # Generate AES key
        aes_key = Fernet.generate_key()
        # Bind encryption to the specific machine guid
        entropy = _get_machine_guid().encode('utf-8')
        enc_key = dpapi_encrypt(aes_key, entropy)
        
        with open(get_path(".master_key"), "wb") as f:
            f.write(enc_key)
        return True
    
    record_failed_attempt()
    return False

def get_aes_key() -> bytes:
    key_path = get_path(".master_key")
    if not os.path.exists(key_path):
        raise LockedException("Master key not found. Vault is locked.")
        
    with open(key_path, "rb") as f:
        enc_key = f.read()
        
    try:
        entropy = _get_machine_guid().encode('utf-8')
        aes_key = dpapi_decrypt(enc_key, entropy)
        return aes_key
    except Exception:
        raise LockedException("Failed to decrypt master key. Vault is locked.")

def encrypt_content(plaintext: str) -> str:
    aes_key = get_aes_key()
    f = Fernet(aes_key)
    return f.encrypt(plaintext.encode("utf-8")).decode("utf-8")

def decrypt_content(ciphertext: str) -> str:
    try:
        aes_key = get_aes_key()
        f = Fernet(aes_key)
        return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except LockedException:
        return "[CONTEÚDO PROTEGIDO POR CRIPTOGRAFIA TOTP]"
    except Exception as e:
        return f"[ERRO DE DECRIPTOGRAFIA: {str(e)}]"

def is_vault_unlocked() -> bool:
    try:
        get_aes_key()
        return True
    except LockedException:
        return False
