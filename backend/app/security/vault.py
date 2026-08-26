"""In-memory holder for the derived encryption key.

Deliberately never persisted anywhere — that's the whole point of the app
password. Cleared whenever the process restarts, which is what makes the
app relock on every container restart. This assumes a single uvicorn
worker process (this project's default) — each worker would otherwise have
its own independent lock state.
"""

from app.services.exceptions import VaultLockedError

_unlocked_key: bytes | None = None


def is_unlocked() -> bool:
    return _unlocked_key is not None


def set_key(key: bytes) -> None:
    global _unlocked_key
    _unlocked_key = key


def get_key() -> bytes:
    if _unlocked_key is None:
        raise VaultLockedError("The vault is locked — unlock it with the app password first.")
    return _unlocked_key


def clear() -> None:
    global _unlocked_key
    _unlocked_key = None
