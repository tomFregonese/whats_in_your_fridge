from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class FridgeInputMode(StrEnum):
    """Batch cooking (main mode) vs. a single dish (simpler sub-case)."""

    BATCH = "batch"
    SINGLE = "single"


@dataclass
class FridgeInputItem:
    """One structured ingredient entry attached to a `FridgeInput`.

    `fridge_stock_item_id` is set when this entry came from picking a chip
    on `FridgeStockPicker` (frontend) rather than being typed one-off — it
    links back to the persistent `FridgeStockItem` (see
    `app.domain.fridge_stock`) so the `RECIPES` phase can later tell the
    model its id (see `agent/prompts.py::_format_item`) and, once the model
    reports using it, `FridgeStockService.deduct()` knows which stock row
    to remove. `None` for free-typed, not-tracked-in-stock ingredients.
    """

    id: int | None
    fridge_input_id: int | None
    ingredient_name: str
    quantity_value: float | None
    quantity_unit: str | None
    quantity_raw: str | None
    fridge_stock_item_id: int | None = None


@dataclass
class FridgeInput:
    """One user submission: structured items and/or free text.

    `items` is populated by the repository when it assembles the full
    aggregate (a separate query joins the `fridge_input_item` rows) — right
    after `FridgeInputEntity.to_domain()` alone it is always empty.
    """

    id: int | None
    mode: FridgeInputMode
    free_text: str | None
    created_at: datetime
    items: list[FridgeInputItem] = field(default_factory=list)
