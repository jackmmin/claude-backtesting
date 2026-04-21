import os
from cryptography.fernet import Fernet

_KEY_PATH = os.path.join(os.path.dirname(__file__), "..", ".cipher.key")


def _load_or_create_key():
    key_path = os.path.abspath(_KEY_PATH)
    if os.path.exists(key_path):
        with open(key_path, "rb") as f:
            return f.read()
    key = Fernet.generate_key()
    with open(key_path, "wb") as f:
        f.write(key)
    return key


def encrypt_secret(secret: str) -> str:
    f = Fernet(_load_or_create_key())
    return f.encrypt(secret.encode()).decode()


def decrypt_secret(encrypted: str) -> str:
    f = Fernet(_load_or_create_key())
    return f.decrypt(encrypted.encode()).decode()
