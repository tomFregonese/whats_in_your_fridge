from app.agent import sourcing_check
from app.agent.output_schema import PlatArgs, PlatIngredient
from app.domain.fridge_input import SourcingMode


def _plat(*ingredients: PlatIngredient) -> PlatArgs:
    return PlatArgs(
        nom="Test dish",
        description="d",
        portions=4,
        ingredients=list(ingredients) or [PlatIngredient(nom="carrot")],
        etapes=["step"],
        fridge_days=3,
    )


def test_find_violation_returns_none_when_nothing_needs_buying() -> None:
    plat = _plat(PlatIngredient(nom="carrot", a_acheter=False))

    assert sourcing_check.find_violation(plat) is None


def test_find_violation_flags_first_ingredient_that_needs_buying() -> None:
    plat = _plat(
        PlatIngredient(nom="carrot", a_acheter=False),
        PlatIngredient(nom="lemon", a_acheter=True),
    )

    assert sourcing_check.find_violation(plat) == "lemon"


def test_check_all_is_a_noop_outside_fridge_only_mode() -> None:
    needs_shopping = _plat(PlatIngredient(nom="lemon", a_acheter=True))

    for mode in (SourcingMode.FRIDGE_PLUS_SHOPPING, SourcingMode.SHOPPING_ONLY):
        safe, violations = sourcing_check.check_all([needs_shopping], mode)
        assert safe == [needs_shopping]
        assert violations == []


def test_check_all_splits_safe_and_violating_in_fridge_only_mode() -> None:
    safe_plat = _plat(PlatIngredient(nom="carrot", a_acheter=False))
    bad_plat = _plat(PlatIngredient(nom="lemon", a_acheter=True))

    safe, violations = sourcing_check.check_all(
        [safe_plat, bad_plat], SourcingMode.FRIDGE_ONLY
    )

    assert safe == [safe_plat]
    assert len(violations) == 1
    assert violations[0].plat == bad_plat
    assert violations[0].ingredient == "lemon"


def test_check_all_with_no_violations_in_fridge_only_mode() -> None:
    plats = [_plat(PlatIngredient(nom="carrot", a_acheter=False))]

    safe, violations = sourcing_check.check_all(plats, SourcingMode.FRIDGE_ONLY)

    assert safe == plats
    assert violations == []
