from sqlalchemy import ColumnElement, desc
from sqlmodel import Session, select

from app.domain.preference_note import PreferenceNote
from app.persistence.entities.preference_note_entity import PreferenceNoteEntity


class PreferenceNoteRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_all(self) -> list[PreferenceNote]:
        """Most recent first."""
        # SQLModel types a class-level field access (e.g. `Entity.created_at`)
        # as its plain Python type (`datetime`), even though at runtime it's
        # a SQLAlchemy column construct — a known typing gap, not a real bug.
        order: ColumnElement[bool] = desc(PreferenceNoteEntity.created_at)  # type: ignore[arg-type]
        entities = self._session.exec(select(PreferenceNoteEntity).order_by(order)).all()
        return [entity.to_domain() for entity in entities]

    def add(self, note: PreferenceNote) -> PreferenceNote:
        entity = PreferenceNoteEntity.from_domain(note)
        self._session.add(entity)
        self._session.commit()
        self._session.refresh(entity)
        return entity.to_domain()

    def delete(self, note_id: int) -> bool:
        """Returns True if a row was deleted, False if `note_id` didn't exist."""
        entity = self._session.get(PreferenceNoteEntity, note_id)
        if entity is None:
            return False
        self._session.delete(entity)
        self._session.commit()
        return True
