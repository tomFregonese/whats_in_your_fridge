from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class FridgeInputMode(StrEnum):
    """Batch cooking (main mode) vs. a single dish (simpler sub-case)."""

    BATCH = "batch"
    SINGLE = "single"


class SourcingMode(StrEnum):
    """How strictly a generation should stick to what's already available,
    orthogonal to `FridgeInputMode` (which is about session shape, not
    ingredient sourcing). Read by `agent/prompts.py::build_system_prompt`
    to steer the model, and enforced deterministically for `FRIDGE_ONLY`
    by `agent/sourcing_check.py` — see that module's docstring.
    """

    FRIDGE_ONLY = "fridge_only"
    """Never propose an ingredient that isn't already available (fridge
    selection, free-typed extras, or pantry staples) — no shopping list."""

    FRIDGE_PLUS_SHOPPING = "fridge_plus_shopping"
    """Prefer the fridge, but a few extra ingredients are fine as long as
    they're flagged (`a_acheter`) for the shopping list. The default —
    matches this app's original, only behavior before this enum existed."""

    SHOPPING_ONLY = "shopping_only"
    """Plan freely without trying to use up the fridge — everything beyond
    pantry staples (and whatever fridge items the household opportunistically
    picked) ends up on the shopping list."""


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
    sourcing_mode: SourcingMode = SourcingMode.FRIDGE_PLUS_SHOPPING
    days: int | None = None
    """Number of days this batch-cooking session should cover — only
    meaningful when `mode == BATCH` (see `dto/fridge_input_dto.py`'s
    validation). Sizes the `IDEAS`-phase shortlist (see `agent/prompts.py`)
    and, once the recipes are generated, feeds
    `services/meal_agenda_service.py`'s day assignment. `None` for a
    single-dish submission, or an older batch submission that predates
    this field."""
