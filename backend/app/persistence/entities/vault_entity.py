from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class VaultEntity(SQLModel, table=True):
    """Singleton row (id=1): the app password's KDF material and the
    encrypted OpenRouter token.

    Deliberate exception to the Dto/BO/Entity triptyque used everywhere
    else — see `app.security`'s docstring for why. There is no
    `to_domain()`/`from_domain()` here and no BO: `app.security.service`
    reads and writes this entity directly, and nothing outside `app.security`
    is allowed to import this class.
    """

    __tablename__ = "vault"

    id: int | None = Field(default=None, primary_key=True)
    password_salt: bytes
    password_verifier: bytes
    openrouter_api_token_encrypted: bytes | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
