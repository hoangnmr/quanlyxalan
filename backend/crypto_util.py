"""Symmetric encryption for secrets stored in the DB (e.g. SMTP password).

Uses Fernet (AES-128-CBC + HMAC) with a key deterministically derived from the
app's ``SECRET_KEY`` so no extra key material needs managing. Encrypted values
are opaque, URL-safe base64 strings. Decryption is fail-soft: a value that
cannot be decrypted (wrong key, corrupt) returns "" rather than raising.
"""
from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from .auth import SECRET_KEY


def _fernet() -> Fernet:
    # Derive a stable 32-byte key from SECRET_KEY.
    digest = hashlib.sha256(SECRET_KEY.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(plaintext: str) -> str:
    if not plaintext:
        return ""
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt(ciphertext: str) -> str:
    if not ciphertext:
        return ""
    try:
        return _fernet().decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError, TypeError):
        return ""
