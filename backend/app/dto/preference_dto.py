from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from app.domain.preference_note import PreferenceNote, PreferenceSource


class PreferenceNoteDtoIn(BaseModel):
    content: str = Field(min_length=1)

    def to_domain(self) -> PreferenceNote:
        return PreferenceNote(
            id=None,
            content=self.content.strip(),
            source=PreferenceSource.MANUAL,
            created_at=datetime.now(UTC),
        )


class PreferenceNoteDtoOut(BaseModel):
    id: int
    content: str
    source: str
    created_at: datetime

    @classmethod
    def from_domain(cls, note: PreferenceNote) -> PreferenceNoteDtoOut:
        assert note.id is not None, "PreferenceNoteDtoOut requires a persisted PreferenceNote"
        return cls(
            id=note.id,
            content=note.content,
            source=note.source.value,
            created_at=note.created_at,
        )
