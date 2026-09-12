"""Deterministic, code-level sourcing check — never left to the LLM alone,
same stance as `agent/allergy_check.py` and `agent/equipment_check.py`.

Each ingredient already self-declares `a_acheter` (see `PlatIngredient`);
in `SourcingMode.FRIDGE_ONLY` no ingredient is allowed to need buying, so
any dish with at least one `a_acheter=True` ingredient is a violation. In
the other two modes (`FRIDGE_PLUS_SHOPPING`, `SHOPPING_ONLY`) a shopping
list is expected/desired, so this is a no-op — same shape as
`equipment_check` being called unconditionally and only ever finding
violations when the household actually has a restriction to enforce.
"""

from dataclasses import dataclass

from app.agent.output_schema import PlatArgs
from app.domain.fridge_input import SourcingMode


def find_violation(plat: PlatArgs) -> str | None:
    """Returns the name of the first ingredient `plat` claims needs to be
    bought, else `None`."""
    for ingredient in plat.ingredients:
        if ingredient.a_acheter:
            return ingredient.nom
    return None


@dataclass
class Violation:
    plat: PlatArgs
    ingredient: str


def check_all(
    plats: list[PlatArgs], sourcing_mode: SourcingMode
) -> tuple[list[PlatArgs], list[Violation]]:
    """Splits `plats` into the ones that are safe and the ones that need an
    ingredient bought while the household asked to stick to the fridge.
    Always returns everything as safe when `sourcing_mode` isn't
    `FRIDGE_ONLY`.
    """
    if sourcing_mode != SourcingMode.FRIDGE_ONLY:
        return plats, []

    safe: list[PlatArgs] = []
    violations: list[Violation] = []
    for plat in plats:
        missing = find_violation(plat)
        if missing is None:
            safe.append(plat)
        else:
            violations.append(Violation(plat=plat, ingredient=missing))
    return safe, violations
