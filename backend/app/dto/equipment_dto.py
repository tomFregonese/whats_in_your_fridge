from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.equipment import Equipment


class EquipmentDtoIn(BaseModel):
    name: str = Field(min_length=1)

    def to_domain(self) -> Equipment:
        return Equipment(id=None, name=self.name.strip())


class EquipmentDtoOut(BaseModel):
    id: int
    name: str

    @classmethod
    def from_domain(cls, equipment: Equipment) -> EquipmentDtoOut:
        assert equipment.id is not None, "EquipmentDtoOut requires a persisted Equipment"
        return cls(id=equipment.id, name=equipment.name)
