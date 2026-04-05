"""AES-256-GCM encryption for E2EE cloud sync."""
from __future__ import annotations

import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes


def derive_key(passphrase: str, salt: bytes) -> bytes:
    """Derive a 256-bit key from passphrase using PBKDF2-SHA256."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100_000,
    )
    return kdf.derive(passphrase.encode("utf-8"))


def encrypt_blob(data: bytes, passphrase: str) -> tuple[bytes, bytes, bytes]:
    """Encrypt data with AES-256-GCM. Returns (ciphertext, salt, iv)."""
    salt = os.urandom(16)
    iv = os.urandom(12)
    key = derive_key(passphrase, salt)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(iv, data, None)
    return ciphertext, salt, iv


def decrypt_blob(ciphertext: bytes, passphrase: str, salt: bytes, iv: bytes) -> bytes:
    """Decrypt data with AES-256-GCM. Raises ValueError on wrong passphrase."""
    key = derive_key(passphrase, salt)
    aesgcm = AESGCM(key)
    try:
        return aesgcm.decrypt(iv, ciphertext, None)
    except Exception:
        raise ValueError("Decryption failed — wrong passphrase or corrupted data")
