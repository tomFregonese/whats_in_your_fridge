from datetime import UTC, datetime

from sqlmodel import Session

from app.domain.fridge_input import FridgeInput, FridgeInputItem, FridgeInputMode
from app.persistence.repositories.fridge_input_repository import FridgeInputRepository


def test_add_persists_parent_and_items(session: Session) -> None:
    repo = FridgeInputRepository(session)
    fridge_input = FridgeInput(
        id=None,
        mode=FridgeInputMode.BATCH,
        free_text="also have half a lemon",
        created_at=datetime.now(UTC),
        items=[
            FridgeInputItem(
                id=None,
                fridge_input_id=None,
                ingredient_name="carrot",
                quantity_value=3,
                quantity_unit="pcs",
                quantity_raw=None,
            ),
            FridgeInputItem(
                id=None,
                fridge_input_id=None,
                ingredient_name="rice",
                quantity_value=None,
                quantity_unit=None,
                quantity_raw="a cup",
            ),
        ],
    )

    saved = repo.add(fridge_input)

    assert saved.id is not None
    assert saved.free_text == "also have half a lemon"
    assert len(saved.items) == 2
    assert {item.ingredient_name for item in saved.items} == {"carrot", "rice"}
    assert all(item.fridge_input_id == saved.id for item in saved.items)
    assert all(item.id is not None for item in saved.items)


def test_add_with_no_items_is_allowed(session: Session) -> None:
    repo = FridgeInputRepository(session)
    fridge_input = FridgeInput(
        id=None,
        mode=FridgeInputMode.SINGLE,
        free_text="just some leftover pasta",
        created_at=datetime.now(UTC),
    )

    saved = repo.add(fridge_input)

    assert saved.id is not None
    assert saved.items == []
