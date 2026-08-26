import pytest
from sqlmodel import Session

from app.security.service import SecurityService
from app.services.exceptions import TokenNotConfiguredError, VaultLockedError


def test_has_token_false_before_any_token_set(session: Session) -> None:
    service = SecurityService(session)
    service.setup_password("correct horse battery staple")

    assert service.has_token() is False


def test_get_token_raises_when_never_configured(session: Session) -> None:
    service = SecurityService(session)
    service.setup_password("correct horse battery staple")

    with pytest.raises(TokenNotConfiguredError):
        service.get_token()


def test_set_token_raises_when_vault_locked(session: Session) -> None:
    service = SecurityService(session)

    with pytest.raises(VaultLockedError):
        service.set_token("sk-or-v1-secret")


def test_set_and_get_token_round_trips_through_encryption(session: Session) -> None:
    service = SecurityService(session)
    service.setup_password("correct horse battery staple")

    service.set_token("sk-or-v1-secret-token")

    assert service.has_token() is True
    assert service.get_token() == "sk-or-v1-secret-token"


def test_get_token_after_relock_and_unlock_still_works(session: Session) -> None:
    service = SecurityService(session)
    service.setup_password("correct horse battery staple")
    service.set_token("sk-or-v1-secret-token")

    service.lock()
    service.unlock("correct horse battery staple")

    assert service.get_token() == "sk-or-v1-secret-token"
