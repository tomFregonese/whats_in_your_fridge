from datetime import UTC, datetime, timedelta

from sqlmodel import Session

from app.domain.fridge_input import FridgeInputMode
from app.domain.suggestion import AllergyCheckStatus, MealPlan, Suggestion
from app.persistence.entities.fridge_input_entity import FridgeInputEntity
from app.persistence.entities.suggestion_entity import MealPlanEntity, SuggestionEntity
from app.persistence.repositories.suggestion_repository import SuggestionRepository


def _seed_meal_plan(session: Session, *, created_at: datetime, dish_names: list[str]) -> None:
    """Seeds directly via the entities (bypassing `SuggestionRepository.add`)
    so the dedup-context tests below exercise the read path against data
    the repository itself didn't write.
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


def _fridge_input_id(session: Session) -> int:
    entity = FridgeInputEntity(mode="batch", created_at=datetime.now(UTC))
    session.add(entity)
    session.commit()
    session.refresh(entity)
    assert entity.id is not None
    return entity.id


def _unsaved_suggestion(dish_name: str) -> Suggestion:
    return Suggestion(
        id=None,
        meal_plan_id=None,
        dish_name=dish_name,
        description="A tasty dish",
        ingredients_json='["carrot"]',
        steps_json='["Boil.", "Serve."]',
        servings=4,
        allergy_check_status=AllergyCheckStatus.OK,
    )


def test_add_persists_the_meal_plan_and_its_suggestions(session: Session) -> None:
    fridge_input_id = _fridge_input_id(session)
    now = datetime.now(UTC)

    saved = SuggestionRepository(session).add(
        MealPlan(
            id=None,
            fridge_input_id=fridge_input_id,
            mode=FridgeInputMode.BATCH,
            created_at=now,
            suggestions=[_unsaved_suggestion("Carrot soup"), _unsaved_suggestion("Carrot cake")],
        )
    )

    assert saved.id is not None
    assert saved.fridge_input_id == fridge_input_id
    assert len(saved.suggestions) == 2
    assert all(s.id is not None for s in saved.suggestions)
    assert all(s.meal_plan_id == saved.id for s in saved.suggestions)
    assert [s.dish_name for s in saved.suggestions] == ["Carrot soup", "Carrot cake"]


def test_get_returns_none_for_unknown_id(session: Session) -> None:
    assert SuggestionRepository(session).get(999) is None


def test_get_returns_the_persisted_aggregate(session: Session) -> None:
    fridge_input_id = _fridge_input_id(session)
    repo = SuggestionRepository(session)
    saved = repo.add(
        MealPlan(
            id=None,
            fridge_input_id=fridge_input_id,
            mode=FridgeInputMode.SINGLE,
            created_at=datetime.now(UTC),
            suggestions=[_unsaved_suggestion("Omelette")],
        )
    )
    assert saved.id is not None

    fetched = repo.get(saved.id)

    assert fetched is not None
    assert fetched.mode == FridgeInputMode.SINGLE
    assert [s.dish_name for s in fetched.suggestions] == ["Omelette"]


def test_list_all_orders_most_recent_first(session: Session) -> None:
    fridge_input_id = _fridge_input_id(session)
    repo = SuggestionRepository(session)
    now = datetime.now(UTC)
    repo.add(
        MealPlan(
            id=None,
            fridge_input_id=fridge_input_id,
            mode=FridgeInputMode.BATCH,
            created_at=now - timedelta(days=1),
            suggestions=[_unsaved_suggestion("Old dish")],
        )
    )
    repo.add(
        MealPlan(
            id=None,
            fridge_input_id=fridge_input_id,
            mode=FridgeInputMode.BATCH,
            created_at=now,
            suggestions=[_unsaved_suggestion("New dish")],
        )
    )

    plans = repo.list_all()

    assert [p.suggestions[0].dish_name for p in plans] == ["New dish", "Old dish"]


def test_list_all_empty_when_nothing_persisted(session: Session) -> None:
    assert SuggestionRepository(session).list_all() == []
