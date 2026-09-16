from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from app.domain.fridge_input import FridgeInputMode


class AllergyCheckStatus(StrEnum):
    """Outcome of the deterministic, code-level allergy check — see
    `app.agent.allergy_check`. Never decided by the LLM alone.
    """

    OK = "ok"
    REGENERATED = "regenerated"
    DROPPED = "dropped"


class AgendaStorage(StrEnum):
    """How a given day's `AgendaEntry` expects the dish to be stored by
    the time it's eaten — see `services/meal_agenda_service.py`, which is
    the only place that decides this (never the LLM)."""

    FRESH = "fresh"
    FROZEN = "frozen"
    AT_RISK = "at_risk"


@dataclass
class Suggestion:
    """One proposed dish."""

    id: int | None
    meal_plan_id: int | None
    dish_name: str
    description: str
    ingredients_json: str
    steps_json: str
    servings: int
    allergy_check_status: AllergyCheckStatus
    used_stock_item_ids_json: str = "[]"
    """JSON list of `FridgeStockItem` ids this dish reported using (see
    `agent/output_schema.py::PlatArgs.ingredients_stock_ids`, sanitized by
    `agent/stock_reference_check.py`). Read once, right after a meal plan
    is persisted, by `FridgeStockService.deduct()` — never touched again
    afterward."""
    fridge_days: int = 3
    """Estimated number of days this dish keeps in the fridge after
    cooking — self-reported by the LLM (see `PlatArgs.fridge_days`),
    clamped to a sane range by `agent/conservation_sanity_check.py`. Feeds
    `services/meal_agenda_service.py`'s day assignment; the default of 3
    only applies to rows persisted before this field existed."""
    freezer_friendly: bool = False
    """Whether this dish freezes well — self-reported by the LLM. Also
    feeds `services/meal_agenda_service.py`."""
    leftover_of_suggestion_id: int | None = None
    """Self-referential FK to another `Suggestion` in the same `meal_plan`
    whose leftovers this dish transforms. The LLM only ever names its
    source dish by `dish_name` (see `PlatArgs.restes_de`) — since no id
    exists yet while it's writing that — so this is resolved from that name
    by `SuggestionService._run_recipes_phase` right after the whole batch
    is persisted and real ids exist. Stays `None` for a standalone dish or
    when the LLM's reference didn't match any dish in the batch."""
    leftover_transformation: str | None = None
    """Human-readable note of how the leftovers were transformed (from
    `PlatArgs.transformation`) — kept even in the rare case
    `leftover_of_suggestion_id` couldn't be resolved, so the information
    isn't silently lost."""


@dataclass
class AgendaEntry:
    """One day of a batch-cooking agenda: which dish is eaten (or, for a
    repeat, eaten again) on `day_index` (0 = the day the batch is cooked),
    and how it needs to be stored to get there — see
    `services/meal_agenda_service.py`, the sole deterministic source of
    this, never the LLM. `warning` is set only for `AgendaStorage.AT_RISK`.
    """

    id: int | None
    meal_plan_id: int | None
    day_index: int
    suggestion_id: int
    storage: AgendaStorage
    warning: str | None = None


@dataclass
class MealPlan:
    """The result of one generation: a week's batch-cooking plan, or a
    single dish.

    `suggestions` is populated by the repository when assembling the full
    aggregate, same convention as `FridgeInput.items` — see its docstring.
    `agenda` is populated the same way, and stays empty for single-dish
    plans or batch plans generated without a `days` count.
    """

    id: int | None
    fridge_input_id: int
    mode: FridgeInputMode
    created_at: datetime
    suggestions: list[Suggestion] = field(default_factory=list)
    agenda: list[AgendaEntry] = field(default_factory=list)
