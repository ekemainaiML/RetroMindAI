import base64
import logging
import os

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from core.config import settings

logger = logging.getLogger(__name__)

_cipher: Fernet | None = None


def _get_cipher() -> Fernet:
    global _cipher
    if _cipher is not None:
        return _cipher

    raw_key = settings.encryption_key
    if not raw_key:
        logger.warning("ENCRYPTION_KEY not set — using dev-only derived key")
        raw_key = base64.urlsafe_b64encode(os.urandom(32)).decode()

    try:
        key = base64.urlsafe_b64decode(raw_key.encode())
        if len(key) != 32:
            key = _derive_key(raw_key)
    except Exception:
        key = _derive_key(raw_key)

    _cipher = Fernet(base64.urlsafe_b64encode(key))
    return _cipher


def _derive_key(raw: str) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=b"retromind-enc", iterations=100000)
    return kdf.derive(raw.encode())


def encrypt_file(data: bytes) -> bytes:
    cipher = _get_cipher()
    return cipher.encrypt(data)


def decrypt_file(encrypted: bytes) -> bytes:
    cipher = _get_cipher()
    return cipher.decrypt(encrypted)


def encrypt_field(value: str) -> str:
    cipher = _get_cipher()
    return cipher.encrypt(value.encode()).decode()


def decrypt_field(encrypted: str) -> str:
    cipher = _get_cipher()
    return cipher.decrypt(encrypted.encode()).decode()
