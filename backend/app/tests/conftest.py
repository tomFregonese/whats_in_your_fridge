from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.db import get_session
from app.main import app

# Importing this registers every entity on `SQLModel.metadata` — without it
# `SQLModel.metadata.create_all()` below would create zero tables.
from app.persistence import entities  # noqa: F401
from app.security import vault


@pytest.fixture(autouse=True)
def reset_vault() -> Generator[None, None, None]:
    # `security.vault` holds its unlocked key in a module-level variable
    # (by design — see its docstring), which would otherwise leak the
    # unlocked state from one test into the next.
    vault.clear()
    yield
    vault.clear()


@pytest.fixture(name="session")
def session_fixture() -> Generator[Session, None, None]:
    # In-memory SQLite, one instance shared for the whole test via
    # StaticPool — plain in-memory SQLite gives each new connection a
    # blank database, which breaks FastAPI's request-scoped sessions.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session) -> Generator[TestClient, None, None]:
    def get_session_override() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_session] = get_session_override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
