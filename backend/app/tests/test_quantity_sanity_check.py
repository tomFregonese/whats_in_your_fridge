from app.agent import quantity_sanity_check
from app.agent.output_schema import DictatedItemArgs


def test_drops_a_unit_never_actually_said() -> None:
    # Regression test: the local model reliably invents a plausible unit
    # on a short, single-item transcript — this is the single most common
    # failure observed empirically (e.g. "ten potatoes" -> unit "kg" or
    # "boîte", "milk" -> unit "L").
    item = DictatedItemArgs(
        ingredient_name="potatoes", quantity_value=10, quantity_unit="kg", quantity_raw=None
    )

    quantity_sanity_check.sanitize_quantities([item], "ten potatoes")

    assert item.quantity_unit is None
    assert item.quantity_value == 10


def test_keeps_a_unit_actually_said_including_via_an_alias() -> None:
    # "liters" in the transcript confirms a unit of "L" — not an exact
    # string match, but the same real-world unit.
    item = DictatedItemArgs(
        ingredient_name="milk", quantity_value=2, quantity_unit="L", quantity_raw=None
    )

    quantity_sanity_check.sanitize_quantities([item], "two liters of milk")

    assert item.quantity_unit == "L"


def test_keeps_a_unit_said_in_french_for_an_english_alias() -> None:
    item = DictatedItemArgs(
        ingredient_name="carottes", quantity_value=2, quantity_unit="kg", quantity_raw=None
    )

    quantity_sanity_check.sanitize_quantities([item], "2 kilos de carottes")

    assert item.quantity_unit == "kg"


def test_clears_quantity_raw_when_quantity_value_is_set() -> None:
    # Regression test: the model sometimes echoes the whole transcript
    # into quantity_raw even when it already set a structured
    # quantity_value — the two fields are meant to be mutually exclusive.
    item = DictatedItemArgs(
        ingredient_name="potatoes",
        quantity_value=10,
        quantity_unit=None,
        quantity_raw="ten potatoes",
    )

    quantity_sanity_check.sanitize_quantities([item], "ten potatoes")

    assert item.quantity_raw is None


def test_leaves_quantity_raw_alone_when_quantity_value_is_null() -> None:
    item = DictatedItemArgs(
        ingredient_name="onions", quantity_value=None, quantity_unit=None, quantity_raw="a couple"
    )

    quantity_sanity_check.sanitize_quantities([item], "a couple of onions")

    assert item.quantity_raw == "a couple"


def test_applies_to_every_item() -> None:
    potatoes = DictatedItemArgs(
        ingredient_name="potatoes", quantity_value=10, quantity_unit="kg", quantity_raw="ten"
    )
    carrots = DictatedItemArgs(
        ingredient_name="carrots", quantity_value=3, quantity_unit="kg", quantity_raw="three"
    )

    quantity_sanity_check.sanitize_quantities(
        [potatoes, carrots], "ten potatoes and three carrots"
    )

    assert potatoes.quantity_unit is None
    assert potatoes.quantity_raw is None
    assert carrots.quantity_unit is None
    assert carrots.quantity_raw is None
