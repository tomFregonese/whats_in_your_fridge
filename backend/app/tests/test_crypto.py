import pytest

from app.security import crypto


def test_derive_key_is_deterministic_for_same_password_and_salt() -> None:
    salt = crypto.generate_salt()

    assert crypto.derive_key("hunter2", salt) == crypto.derive_key("hunter2", salt)


def test_derive_key_differs_for_different_passwords() -> None:
    salt = crypto.generate_salt()

    assert crypto.derive_key("hunter2", salt) != crypto.derive_key("hunter3", salt)


def test_derive_key_differs_for_different_salts() -> None:
    assert crypto.derive_key("hunter2", crypto.generate_salt()) != crypto.derive_key(
        "hunter2", crypto.generate_salt()
    )


def test_encrypt_decrypt_round_trip() -> None:
    key = crypto.derive_key("hunter2", crypto.generate_salt())

    ciphertext = crypto.encrypt(key, "sk-or-v1-secret-token")

    assert crypto.decrypt(key, ciphertext) == "sk-or-v1-secret-token"


def test_decrypt_with_wrong_key_raises() -> None:
    salt = crypto.generate_salt()
    key = crypto.derive_key("hunter2", salt)
    wrong_key = crypto.derive_key("wrong-password", salt)
    ciphertext = crypto.encrypt(key, "secret")

    with pytest.raises(crypto.InvalidToken):
        crypto.decrypt(wrong_key, ciphertext)
