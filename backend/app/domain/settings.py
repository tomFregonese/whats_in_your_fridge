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
