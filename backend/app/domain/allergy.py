from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Allergy:
    """A strict exclusion. Checked deterministically in code — see
    `app.agent.allergy_check` — not just left to the LLM's judgment.
    """

    id: int | None
    ingredient_name: str
    notes: str | None
