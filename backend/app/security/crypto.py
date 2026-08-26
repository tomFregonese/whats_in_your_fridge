"""Key derivation + symmetric encryption primitives.

No app-specific logic here (no session, no entity) — just the two building
blocks `security/service.py` composes: turn a password into a key, and
encrypt/decrypt bytes with that key.
"""

import base64
import os

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# OWASP's 2023 minimum recommendation for PBKDF2-HMAC-SHA256. This runs
# once per unlock, not per-request, so the extra ~200ms cost is invisible.
PBKDF2_ITERATIONS = 600_000
SALT_LENGTH_BYTES = 16

__all__ = ["InvalidToken", "decrypt", "derive_key", "encrypt", "generate_salt"]


def generate_salt() -> bytes:
    return os.urandom(SALT_LENGTH_BYTES)


def derive_key(password: str, salt: bytes) -> bytes:
    """Derives a Fernet-compatible key (32 url-safe-base64 bytes) from the
    app password. Deterministic for a given (password, salt) pair — that's
    what lets `unlock` re-derive the exact same key later without ever
    storing it.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))


def encrypt(key: bytes, plaintext: str) -> bytes:
    return Fernet(key).encrypt(plaintext.encode("utf-8"))


def decrypt(key: bytes, token: bytes) -> str:
    """Raises `InvalidToken` if `key` is wrong or `token` was corrupted —
    this doubles as the password check in `security/service.py`, so there's
    no separate password hash to store.
    """
    return Fernet(key).decrypt(token).decode("utf-8")
