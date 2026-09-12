"""Deterministic, code-level equipment check — never left to the LLM
alone, same stance as `agent/allergy_check.py`.

Each dish self-declares `equipment_used` (see `PlatArgs`, mirrors
`ingredients_stock_ids`); this compares that list against the household's
available equipment (see `app.domain.equipment.Equipment`) using
normalized (case- and accent-insensitive) matching in *either* direction —
"oven" claimed against a household entry of "electric oven" (or the
reverse) both count as a match. That's deliberately more permissive than
`allergy_check`'s one-directional substring rule: a false negative here
just under-restricts (a dish looks fine when it technically named
equipment slightly differently), which is an acceptable trade-off for a
convenience constraint — unlike an allergy, nothing unsafe slips through.
A stovetop, pots/pans, knives and basic utensils are always assumed
available (see `agent.prompts.BASE_EQUIPMENT`) and are never checked here.
"""

from dataclasses import dataclass

from app.agent.output_schema import PlatArgs
from app.agent.text_normalize import normalize
from app.domain.equipment import Equipment


def _matches(claimed: str, available: str) -> bool:
    return claimed in available or available in claimed


def find_violation(plat: PlatArgs, equipment: list[Equipment]) -> str | None:
    """Returns the first piece of equipment `plat` claims to use that
    isn't available at the household, else `None`."""
    available_names = [normalize(item.name) for item in equipment]
    for used in plat.equipment_used:
        used_norm = normalize(used)
        if not used_norm:
            continue
        if not any(_matches(used_norm, available) for available in available_names):
            return used
    return None


@dataclass
class Violation:
    plat: PlatArgs
    equipment: str


def check_all(
    plats: list[PlatArgs], equipment: list[Equipment]
) -> tuple[list[PlatArgs], list[Violation]]:
    """Splits `plats` into the ones that are safe and the ones that use
    equipment the household doesn't have, paired with which piece of
    equipment matched.
    """
    safe: list[PlatArgs] = []
    violations: list[Violation] = []
    for plat in plats:
        missing = find_violation(plat, equipment)
        if missing is None:
            safe.append(plat)
        else:
            violations.append(Violation(plat=plat, equipment=missing))
    return safe, violations
