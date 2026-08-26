"""Setup/unlock/lock orchestration for the app password.

The only place outside `security/crypto.py` and `security/vault.py`
allowed to touch `VaultEntity` directly — see `app.security`'s docstring
for why this bypasses the usual Dto/BO/Entity triptyque. Encrypting/storing
the OpenRouter token itself is added in a later milestone (once the token
entry screen exists) — this milestone only builds the password mechanism.
"""

from datetime import UTC, datetime

from sqlmodel import Session

from app.persistence.entities.vault_entity import VaultEntity
from app.security import crypto, vault
from app.services.exceptions import InvalidPasswordError, PasswordAlreadySetError

SINGLETON_ID = 1

# A fixed, known plaintext encrypted at setup time and re-decrypted on every
# unlock attempt: success proves the password is correct (Fernet's built-in
# authentication rejects a wrong key), so no separate password hash table
# is needed.
VERIFIER_PLAINTEXT = "whats-in-your-fridge-vault-ok"


class SecurityService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def is_password_set(self) -> bool:
        return self._session.get(VaultEntity, SINGLETON_ID) is not None

    def is_unlocked(self) -> bool:
        return vault.is_unlocked()

    def setup_password(self, password: str) -> None:
        if self.is_password_set():
            raise PasswordAlreadySetError("The app password has already been set.")

        salt = crypto.generate_salt()
        key = crypto.derive_key(password, salt)
        verifier = crypto.encrypt(key, VERIFIER_PLAINTEXT)

        now = datetime.now(UTC)
        entity = VaultEntity(
            id=SINGLETON_ID,
            password_salt=salt,
            password_verifier=verifier,
            openrouter_api_token_encrypted=None,
            created_at=now,
            updated_at=now,
        )
        self._session.add(entity)
        self._session.commit()

        vault.set_key(key)

    def unlock(self, password: str) -> None:
        entity = self._session.get(VaultEntity, SINGLETON_ID)
        if entity is None:
            raise InvalidPasswordError("No app password has been set yet.")

        key = crypto.derive_key(password, entity.password_salt)
        try:
            crypto.decrypt(key, entity.password_verifier)
        except crypto.InvalidToken as exc:
            raise InvalidPasswordError("Incorrect password.") from exc

        vault.set_key(key)

    def lock(self) -> None:
        vault.clear()
