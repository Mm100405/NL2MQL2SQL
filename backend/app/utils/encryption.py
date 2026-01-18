import base64
from cryptography.fernet import Fernet
from app.config import settings

# Generate a key from settings (ensure it's 32 bytes for Fernet)
def _get_fernet():
    key = settings.ENCRYPTION_KEY.encode()
    # Ensure key is 32 bytes and base64 encoded
    key = base64.urlsafe_b64encode(key[:32].ljust(32, b'0'))
    return Fernet(key)


def encrypt_api_key(api_key: str) -> str:
    """Encrypt an API key for storage"""
    if not api_key:
        return None
    f = _get_fernet()
    return f.encrypt(api_key.encode()).decode()


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt an API key for use"""
    if not encrypted_key:
        return None
    f = _get_fernet()
    return f.decrypt(encrypted_key.encode()).decode()
