from app.agent import stock_reference_check
from app.agent.output_schema import PlatArgs, PlatIngredient


def _plat(*stock_ids: int) -> PlatArgs:
    return PlatArgs(
        nom="Test dish",
        description="d",
        portions=4,
        ingredients=[PlatIngredient(nom="carrot")],
        etapes=["step"],
        ingredients_stock_ids=list(stock_ids),
    )


def test_sanitize_keeps_known_ids() -> None:
    plat = _plat(1, 2, 3)

    stock_reference_check.sanitize_stock_ids([plat], {1, 2, 3})

    assert plat.ingredients_stock_ids == [1, 2, 3]


def test_sanitize_drops_unknown_ids() -> None:
    # 99 was never offered to the model — a hallucinated or stale ID must
    # not survive to reach `FridgeStockService.deduct()`.
    plat = _plat(1, 99, 2)

    stock_reference_check.sanitize_stock_ids([plat], {1, 2})

    assert plat.ingredients_stock_ids == [1, 2]


def test_sanitize_with_no_known_ids_drops_everything() -> None:
    plat = _plat(1, 2)

    stock_reference_check.sanitize_stock_ids([plat], set())

    assert plat.ingredients_stock_ids == []


def test_sanitize_applies_to_every_plat() -> None:
    plat_a = _plat(1, 5)
    plat_b = _plat(2, 5)

    stock_reference_check.sanitize_stock_ids([plat_a, plat_b], {1, 2})

    assert plat_a.ingredients_stock_ids == [1]
    assert plat_b.ingredients_stock_ids == [2]
