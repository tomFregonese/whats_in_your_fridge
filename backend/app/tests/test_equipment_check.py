from app.agent import equipment_check
from app.agent.output_schema import PlatArgs, PlatIngredient
from app.domain.equipment import Equipment


def _plat(*equipment_used: str) -> PlatArgs:
    return PlatArgs(
        nom="Test dish",
        description="d",
        portions=4,
        ingredients=[PlatIngredient(nom="carrot")],
        etapes=["step"],
        equipment_used=list(equipment_used),
        fridge_days=3,
    )


def test_find_violation_returns_none_when_only_baseline_needed() -> None:
    plat = _plat()

    assert equipment_check.find_violation(plat, []) is None


def test_find_violation_returns_none_when_equipment_available() -> None:
    plat = _plat("oven")
    equipment = [Equipment(id=1, name="oven")]

    assert equipment_check.find_violation(plat, equipment) is None


def test_find_violation_flags_missing_equipment() -> None:
    plat = _plat("oven")

    assert equipment_check.find_violation(plat, []) == "oven"


def test_find_violation_is_case_and_accent_insensitive() -> None:
    plat = _plat("MIXEUR")
    equipment = [Equipment(id=1, name="mixeur électrique")]

    assert equipment_check.find_violation(plat, equipment) is None


def test_find_violation_matches_either_direction() -> None:
    # A household entry of "oven" satisfies a dish claiming "electric oven"
    # (and vice versa) — more permissive than the allergy check on purpose,
    # see `equipment_check.py`'s docstring.
    plat = _plat("electric oven")
    equipment = [Equipment(id=1, name="oven")]

    assert equipment_check.find_violation(plat, equipment) is None


def test_find_violation_checks_every_claimed_item() -> None:
    plat = _plat("oven", "blender")
    equipment = [Equipment(id=1, name="oven")]

    assert equipment_check.find_violation(plat, equipment) == "blender"


def test_check_all_splits_safe_and_violating() -> None:
    safe_plat = _plat()
    bad_plat = _plat("oven")

    safe, violations = equipment_check.check_all([safe_plat, bad_plat], [])

    assert safe == [safe_plat]
    assert len(violations) == 1
    assert violations[0].plat == bad_plat
    assert violations[0].equipment == "oven"


def test_check_all_with_no_violations() -> None:
    plats = [_plat(), _plat("oven")]
    equipment = [Equipment(id=1, name="oven")]

    safe, violations = equipment_check.check_all(plats, equipment)

    assert safe == plats
    assert violations == []
