from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Equipment:
    """One piece of kitchen equipment the household owns (e.g. "oven",
    "blender") — a stovetop, pots/pans, knives and basic utensils are
    always assumed available (see `agent.prompts.BASE_EQUIPMENT`) and
    never need to be listed here. Checked deterministically in code — see
    `app.agent.equipment_check` — not just left to the LLM's judgment,
    same stance as `app.domain.allergy.Allergy`.
    """

    id: int | None
    name: str
