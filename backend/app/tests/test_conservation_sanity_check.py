from app.agent.conservation_sanity_check import (
    MAX_FRIDGE_DAYS,
    MIN_FRIDGE_DAYS,
    sanitize_fridge_days,
)
from app.agent.output_schema import PlatArgs, PlatIngredient


def _plat(fridge_days: int) -> PlatArgs:
    return PlatArgs(
        nom="Test dish",
        description="d",
        portions=4,
        ingredients=[PlatIngredient(nom="carrot")],
        etapes=["step"],
        fridge_days=fridge_days,
    )


def test_sanitize_leaves_a_plausible_value_untouched() -> None:
    plat = _plat(4)

    sanitize_fridge_days([plat])

    assert plat.fridge_days == 4


def test_sanitize_clamps_an_implausibly_high_value() -> None:
    plat = _plat(365)

    sanitize_fridge_days([plat])

    assert plat.fridge_days == MAX_FRIDGE_DAYS


def test_sanitize_clamps_to_the_minimum() -> None:
    # `PlatArgs.fridge_days` already enforces `gt=0` at the schema level,
    # so this only exercises the clamp's own lower bound directly.
    plat = _plat(1)
    plat.fridge_days = 0

    sanitize_fridge_days([plat])

    assert plat.fridge_days == MIN_FRIDGE_DAYS


def test_sanitize_applies_to_every_plat() -> None:
    plat_a = _plat(2)
    plat_b = _plat(99)

    sanitize_fridge_days([plat_a, plat_b])

    assert plat_a.fridge_days == 2
    assert plat_b.fridge_days == MAX_FRIDGE_DAYS
