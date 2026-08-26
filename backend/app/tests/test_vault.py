import pytest

from app.security import vault
from app.services.exceptions import VaultLockedError


def test_locked_by_default() -> None:
    assert vault.is_unlocked() is False


def test_get_key_raises_while_locked() -> None:
    with pytest.raises(VaultLockedError):
        vault.get_key()


def test_set_key_unlocks_and_clear_relocks() -> None:
    vault.set_key(b"some-key")
    assert vault.is_unlocked() is True
    assert vault.get_key() == b"some-key"

    vault.clear()
    assert vault.is_unlocked() is False
