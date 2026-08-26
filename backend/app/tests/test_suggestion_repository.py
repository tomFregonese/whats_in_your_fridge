from datetime import UTC, datetime, timedelta

from sqlmodel import Session

from app.persistence.entities.fridge_input_entity import FridgeInputEntity
from app.persistence.entities.suggestion_entity import MealPlanEntity, SuggestionEntity
from app.persistence.repositories.suggestion_repository import SuggestionRepository


def _seed_meal_plan(session: Session, *, created_at: datetime, dish_names: list[str]) -> None:
    """Bypasses the repository layer on purpose: nothing writes
    meal_plan/suggestion rows yet in the real flow (see
    SuggestionRepository's docstring), so tests seed directly via the
    entities to exercise the read path against real data.
    """
    fridge_input = FridgeInputEntity(mode="batch", created_at=created_at)
    session.add(fridge_input)
    session.flush()
    assert fridge_input.id is not None

    meal_plan = MealPlanEntity(fridge_input_id=fridge_input.id, mode="batch", created_at=created_at)
    session.add(meal_plan)
    session.flush()
    assert meal_plan.id is not None

    for name in dish_names:
        session.add(
            SuggestionEntity(
                meal_plan_id=meal_plan.id,
                dish_name=name,
                description="d",
                ingredients_json="[]",
                steps_json="[]",
                servings=4,
                allergy_check_status="ok",
            )
        )
    session.commit()


def test_list_recent_dish_names_empty_when_no_history(session: Session) -> None:
    repo = SuggestionRepository(session)

    assert repo.list_recent_dish_names(limit=10) == []


def test_list_recent_dish_names_orders_by_meal_plan_recency(session: Session) -> None:
    now = datetime.now(UTC)
    _seed_meal_plan(session, created_at=now - timedelta(days=2), dish_names=["Old soup"])
    _seed_meal_plan(session, created_at=now, dish_names=["Fresh salad"])

    names = SuggestionRepository(session).list_recent_dish_names(limit=10)

    assert names == ["Fresh salad", "Old soup"]


def test_list_recent_dish_names_respects_limit(session: Session) -> None:
    now = datetime.now(UTC)
    _seed_meal_plan(session, created_at=now - timedelta(days=2), dish_names=["Old soup"])
    _seed_meal_plan(session, created_at=now, dish_names=["Fresh salad"])

    names = SuggestionRepository(session).list_recent_dish_names(limit=1)

    assert names == ["Fresh salad"]


def test_list_recent_dish_names_includes_every_dish_in_a_plan(session: Session) -> None:
    now = datetime.now(UTC)
    _seed_meal_plan(session, created_at=now, dish_names=["Soup", "Salad", "Stew"])

    names = SuggestionRepository(session).list_recent_dish_names(limit=10)

    assert set(names) == {"Soup", "Salad", "Stew"}
