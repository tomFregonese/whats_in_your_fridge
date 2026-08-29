from datetime import UTC, datetime

from sqlmodel import Session, select

from app.domain.merge_dismissal import MergeDismissal
from app.persistence.entities.merge_dismissal_entity import MergeDismissalEntity


class MergeDismissalRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _normalize_pair(name_a: str, name_b: str) -> tuple[str, str]:
        a, b = sorted((name_a.strip().lower(), name_b.strip().lower()))
        return a, b

    def is_dismissed(self, name_a: str, name_b: str) -> bool:
        a, b = self._normalize_pair(name_a, name_b)
        condition = (MergeDismissalEntity.name_a == a) & (MergeDismissalEntity.name_b == b)
        return self._session.exec(select(MergeDismissalEntity).where(condition)).first() is not None

    def dismiss(self, name_a: str, name_b: str) -> MergeDismissal:
        """Idempotent — dismissing an already-dismissed pair returns the
        existing row rather than violating the unique constraint."""
        a, b = self._normalize_pair(name_a, name_b)
        condition = (MergeDismissalEntity.name_a == a) & (MergeDismissalEntity.name_b == b)
        existing = self._session.exec(select(MergeDismissalEntity).where(condition)).first()
        if existing is not None:
            return existing.to_domain()

        entity = MergeDismissalEntity(name_a=a, name_b=b, created_at=datetime.now(UTC))
        self._session.add(entity)
        self._session.commit()
        self._session.refresh(entity)
        return entity.to_domain()
