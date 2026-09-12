from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Settings:
    """Instance-wide settings — there is exactly one row (id=1).

    Everything the user configures that isn't a secret lives here: default
    portions and the chosen OpenRouter model. The OpenRouter token itself
    lives in the `vault` table instead — see `app.security`.
    """

    id: int | None
    default_servings: int
    openrouter_model_id: str | None
    created_at: datetime
    updated_at: datetime
    freezer_capacity_slots: int | None = None
    """Household freezer capacity, in number of dish portions (same unit
    as `default_servings` sizes a dish) — `None` means unlimited, the
    default until the user sets one, so no household sees a capacity
    warning it never opted into. Consulted by
    `services/meal_agenda_service.py::build_agenda` when deciding whether
    a dish that would otherwise spoil can be frozen instead."""
