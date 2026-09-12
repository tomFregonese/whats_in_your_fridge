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
    fridge_stock_item_id: int | None = None


MIN_DAYS = 1
MAX_DAYS = 14


class FridgeInputDtoIn(BaseModel):
    """Structured items and/or free text — usable separately or together,
    per the original brief. At least one of the two must be provided.

    `days` is only meaningful in `batch` mode — how many days this
    batch-cooking session should cover, sizing the idea shortlist (see
    `agent/prompts.py`) and later feeding the agenda scheduler (see
    `services/meal_agenda_service.py`). Required in `batch` mode,
    ignored (forced to `None`) in `single` mode.
    """

    mode: Literal["batch", "single"] = "batch"
    free_text: str | None = None
    items: list[FridgeInputItemDtoIn] = Field(default_factory=list)
    days: int | None = Field(default=None, ge=MIN_DAYS, le=MAX_DAYS)

    @model_validator(mode="after")
    def _require_items_or_free_text(self) -> Self:
        if not self.items and not (self.free_text and self.free_text.strip()):
            raise ValueError("Provide at least one ingredient or some free text.")
        return self

    @model_validator(mode="after")
    def _require_days_in_batch_mode(self) -> Self:
        if self.mode == "batch" and self.days is None:
            raise ValueError("`days` is required in batch mode.")
        return self

    def to_domain(self) -> FridgeInput:
        now = datetime.now(UTC)
        return FridgeInput(
            id=None,
            mode=FridgeInputMode(self.mode),
            free_text=self.free_text,
            created_at=now,
            days=self.days if self.mode == "batch" else None,
            items=[
                FridgeInputItem(
                    id=None,
                    fridge_input_id=None,
                    ingredient_name=item.ingredient_name.strip(),
                    quantity_value=item.quantity_value,
                    quantity_unit=item.quantity_unit,
                    quantity_raw=item.quantity_raw,
                    fridge_stock_item_id=item.fridge_stock_item_id,
                )
                for item in self.items
            ],
        )
