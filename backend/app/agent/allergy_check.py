"""Deterministic, code-level allergy check — never left to the LLM alone.

Compares each proposed dish's ingredients against the household's strict
allergy list using normalized (case- and accent-insensitive) substring
matching: an allergy is violated if its name appears anywhere inside an
ingredient's name. This deliberately only checks one direction (allergen
in ingredient, not the reverse) — checking the reverse would flag things
like a generic "oil" ingredient against an "olive oil" allergy, which
isn't what a strict exclusion list means.
"""

from dataclasses import dataclass

from app.agent.output_schema import PlatArgs
from app.agent.text_normalize import normalize
from app.domain.allergy import Allergy


def find_violation(plat: PlatArgs, allergies: list[Allergy]) -> str | None:
    """Returns the matched allergy's ingredient name if `plat` violates it,
    else `None`. Returns the first match found; a dish can only be
    reported as violating once even if it breaks several allergies — one
    is enough to exclude it.
    """
    ingredient_names = [normalize(ingredient.nom) for ingredient in plat.ingredients]
    for allergy in allergies:
        allergen = normalize(allergy.ingredient_name)
        if not allergen:
            continue
        if any(allergen in name for name in ingredient_names):
            return allergy.ingredient_name
    return None


@dataclass
class Violation:
    plat: PlatArgs
    allergen: str


def check_all(
    plats: list[PlatArgs], allergies: list[Allergy]
) -> tuple[list[PlatArgs], list[Violation]]:
    """Splits `plats` into the ones that are safe and the ones that violate
    a strict allergy, paired with which allergen matched.
    """
    safe: list[PlatArgs] = []
    violations: list[Violation] = []
    for plat in plats:
        allergen = find_violation(plat, allergies)
        if allergen is None:
            safe.append(plat)
        else:
            violations.append(Violation(plat=plat, allergen=allergen))
    return safe, violations
