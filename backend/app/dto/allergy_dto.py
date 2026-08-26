from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.allergy import Allergy


class AllergyDtoIn(BaseModel):
    ingredient_name: str = Field(min_length=1)
    notes: str | None = None

    def to_domain(self) -> Allergy:
        return Allergy(id=None, ingredient_name=self.ingredient_name.strip(), notes=self.notes)


class AllergyDtoOut(BaseModel):
    id: int
    ingredient_name: str
    notes: str | None

    @classmethod
    def from_domain(cls, allergy: Allergy) -> AllergyDtoOut:
        assert allergy.id is not None, "AllergyDtoOut requires a persisted Allergy"
        return cls(id=allergy.id, ingredient_name=allergy.ingredient_name, notes=allergy.notes)
