from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel, UniqueConstraint

from app.domain.merge_dismissal import MergeDismissal


class MergeDismissalEntity(SQLModel, table=True):
    __tablename__ = "merge_dismissal"
    __table_args__ = (UniqueConstraint("name_a", "name_b", name="uq_merge_dismissal_pair"),)

    id: int | None = Field(default=None, primary_key=True)
    name_a: str = Field(index=True)
    name_b: str = Field(index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def to_domain(self) -> MergeDismissal:
        return MergeDismissal(
            id=self.id, name_a=self.name_a, name_b=self.name_b, created_at=self.created_at
        )

    @classmethod
    def from_domain(cls, dismissal: MergeDismissal) -> MergeDismissalEntity:
        return cls(
            id=dismissal.id,
            name_a=dismissal.name_a,
            name_b=dismissal.name_b,
            created_at=dismissal.created_at,
        )
