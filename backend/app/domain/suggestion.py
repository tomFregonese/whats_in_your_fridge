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


@dataclass
class MealPlan:
    """The result of one generation: a week's batch-cooking plan, or a
    single dish.

    `suggestions` is populated by the repository when assembling the full
    aggregate, same convention as `FridgeInput.items` — see its docstring.
    """

    id: int | None
    fridge_input_id: int
    mode: FridgeInputMode
    created_at: datetime
    suggestions: list[Suggestion] = field(default_factory=list)
