from __future__ import annotations

from sqlmodel import Field, SQLModel

from app.domain.allergy import Allergy


class AllergyEntity(SQLModel, table=True):
    __tablename__ = "allergy"

    id: int | None = Field(default=None, primary_key=True)
    ingredient_name: str = Field(index=True)
    notes: str | None = None

    def to_domain(self) -> Allergy:
        return Allergy(
            id=self.id,
            ingredient_name=self.ingredient_name,
            notes=self.notes,
        )

    @classmethod
    def from_domain(cls, allergy: Allergy) -> AllergyEntity:
        return cls(
            id=allergy.id,
            ingredient_name=allergy.ingredient_name,
            notes=allergy.notes,
        )
