from collections.abc import Generator

from sqlmodel import Session, create_engine

from app.config import settings

# `check_same_thread=False`: FastAPI may serve a request on a different
# thread than the one that created the engine. This is safe here because
# every request gets its own `Session` (see `get_session` below) rather
# than sharing one across threads.
engine = create_engine(
    f"sqlite:///{settings.db_path}",
    connect_args={"check_same_thread": False},
)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency: yields one `Session` per request.

    Usage in a controller: ``session: Session = Depends(get_session)``.
    """
    with Session(engine) as session:
        yield session
