from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator

from app.domain.fridge_input import FridgeInput, FridgeInputItem, FridgeInputMode


class FridgeInputItemDtoIn(BaseModel):
    ingredient_name: str = Field(min_length=1)
    quantity_value: float | None = None
    quantity_unit: str | None = None
    quantity_raw: str | None = None


class FridgeInputDtoIn(BaseModel):
    """Structured items and/or free text — usable separately or together,
    per the original brief. At least one of the two must be provided.
    """

    mode: Literal["batch", "single"] = "batch"
    free_text: str | None = None
    items: list[FridgeInputItemDtoIn] = Field(default_factory=list)

    @model_validator(mode="after")
    def _require_items_or_free_text(self) -> Self:
        if not self.items and not (self.free_text and self.free_text.strip()):
            raise ValueError("Provide at least one ingredient or some free text.")
        return self

    def to_domain(self) -> FridgeInput:
        now = datetime.now(UTC)
        return FridgeInput(
            id=None,
            mode=FridgeInputMode(self.mode),
            free_text=self.free_text,
            created_at=now,
            items=[
                FridgeInputItem(
                    id=None,
                    fridge_input_id=None,
                    ingredient_name=item.ingredient_name.strip(),
                    quantity_value=item.quantity_value,
                    quantity_unit=item.quantity_unit,
                    quantity_raw=item.quantity_raw,
                )
                for item in self.items
            ],
        )
