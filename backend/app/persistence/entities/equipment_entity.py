from __future__ import annotations

from sqlmodel import Field, SQLModel

from app.domain.equipment import Equipment


class EquipmentEntity(SQLModel, table=True):
    __tablename__ = "equipment"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)

    def to_domain(self) -> Equipment:
        return Equipment(id=self.id, name=self.name)

    @classmethod
    def from_domain(cls, equipment: Equipment) -> EquipmentEntity:
        return cls(id=equipment.id, name=equipment.name)
