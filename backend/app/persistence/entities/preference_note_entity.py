from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel

from app.domain.preference_note import PreferenceNote, PreferenceSource


class PreferenceNoteEntity(SQLModel, table=True):
    __tablename__ = "preference_note"

    id: int | None = Field(default=None, primary_key=True)
    content: str
    source: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)

    def to_domain(self) -> PreferenceNote:
        return PreferenceNote(
            id=self.id,
            content=self.content,
            source=PreferenceSource(self.source),
            created_at=self.created_at,
        )

    @classmethod
    def from_domain(cls, note: PreferenceNote) -> PreferenceNoteEntity:
        return cls(
            id=note.id,
            content=note.content,
            source=note.source.value,
            created_at=note.created_at,
        )
