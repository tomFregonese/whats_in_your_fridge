from app.agent import allergy_check
from app.agent.output_schema import PlatArgs, PlatIngredient
from app.domain.allergy import Allergy


def _plat(*ingredient_names: str) -> PlatArgs:
    return PlatArgs(
        nom="Test dish",
        description="d",
        portions=4,
        ingredients=[PlatIngredient(nom=name) for name in ingredient_names],
        etapes=["step"],
    )


def test_find_violation_returns_none_when_clean() -> None:
    plat = _plat("carrot", "rice")
    allergies = [Allergy(id=1, ingredient_name="peanut", notes=None)]

    assert allergy_check.find_violation(plat, allergies) is None


def test_find_violation_matches_exact_ingredient() -> None:
    plat = _plat("peanut")
    allergies = [Allergy(id=1, ingredient_name="peanut", notes=None)]

    assert allergy_check.find_violation(plat, allergies) == "peanut"


def test_find_violation_matches_substring() -> None:
    # "peanut butter" contains the allergen "peanut" — must be caught even
    # though it's not an exact match.
    plat = _plat("peanut butter")
    allergies = [Allergy(id=1, ingredient_name="peanut", notes=None)]

    assert allergy_check.find_violation(plat, allergies) == "peanut"


def test_find_violation_is_case_insensitive() -> None:
    plat = _plat("PEANUT butter")
    allergies = [Allergy(id=1, ingredient_name="Peanut", notes=None)]

    assert allergy_check.find_violation(plat, allergies) == "Peanut"


def test_find_violation_is_accent_insensitive() -> None:
    plat = _plat("creme fraiche")
    allergies = [Allergy(id=1, ingredient_name="crème", notes=None)]

    assert allergy_check.find_violation(plat, allergies) == "crème"


def test_find_violation_checks_every_ingredient() -> None:
    plat = _plat("rice", "peanut oil", "carrot")
    allergies = [Allergy(id=1, ingredient_name="peanut", notes=None)]

    assert allergy_check.find_violation(plat, allergies) == "peanut"


def test_find_violation_with_no_allergies_never_violates() -> None:
    plat = _plat("peanut", "shellfish", "anything")

    assert allergy_check.find_violation(plat, []) is None


def test_find_violation_does_not_match_reverse_direction() -> None:
    # A generic "oil" ingredient must NOT trip an "olive oil" allergy —
    # only allergen-in-ingredient is checked, never the reverse.
    plat = _plat("oil")
    allergies = [Allergy(id=1, ingredient_name="olive oil", notes=None)]

    assert allergy_check.find_violation(plat, allergies) is None


def test_check_all_splits_safe_and_violating() -> None:
    safe_plat = _plat("carrot", "rice")
    bad_plat = _plat("peanut butter")
    allergies = [Allergy(id=1, ingredient_name="peanut", notes=None)]

    safe, violations = allergy_check.check_all([safe_plat, bad_plat], allergies)

    assert safe == [safe_plat]
    assert len(violations) == 1
    assert violations[0].plat == bad_plat
    assert violations[0].allergen == "peanut"


def test_check_all_with_no_violations() -> None:
    plats = [_plat("carrot"), _plat("rice")]

    safe, violations = allergy_check.check_all(plats, [])

    assert safe == plats
    assert violations == []
