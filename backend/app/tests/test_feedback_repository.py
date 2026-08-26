from datetime import UTC, datetime

from sqlmodel import Session

from app.domain.feedback import Feedback
from app.domain.fridge_input import FridgeInputMode
from app.domain.suggestion import AllergyCheckStatus, MealPlan, Suggestion
from app.persistence.entities.fridge_input_entity import FridgeInputEntity
from app.persistence.repositories.feedback_repository import FeedbackRepository
from app.persistence.repositories.suggestion_repository import SuggestionRepository


def _seed_suggestion(session: Session) -> int:
    fridge_input = FridgeInputEntity(mode="batch", created_at=datetime.now(UTC))
    session.add(fridge_input)
    session.commit()
    session.refresh(fridge_input)
    assert fridge_input.id is not None

    saved = SuggestionRepository(session).add(
        MealPlan(
            id=None,
            fridge_input_id=fridge_input.id,
            mode=FridgeInputMode.BATCH,
            created_at=datetime.now(UTC),
            suggestions=[
                Suggestion(
                    id=None,
                    meal_plan_id=None,
                    dish_name="Soup",
                    description="d",
                    ingredients_json="[]",
                    steps_json="[]",
                    servings=4,
                    allergy_check_status=AllergyCheckStatus.OK,
                )
            ],
        )
    )
    suggestion_id = saved.suggestions[0].id
    assert suggestion_id is not None
    return suggestion_id


def test_get_by_suggestion_returns_none_when_no_feedback_yet(session: Session) -> None:
    suggestion_id = _seed_suggestion(session)

    assert FeedbackRepository(session).get_by_suggestion(suggestion_id) is None


def test_upsert_creates_a_new_row(session: Session) -> None:
    suggestion_id = _seed_suggestion(session)

    saved = FeedbackRepository(session).upsert(
        Feedback(id=None, suggestion_id=suggestion_id, liked=True, comment="Great")
    )

    assert saved.id is not None
    assert saved.liked is True
    assert saved.comment == "Great"


def test_upsert_updates_the_existing_row_for_the_same_suggestion(session: Session) -> None:
    suggestion_id = _seed_suggestion(session)
    repo = FeedbackRepository(session)
    first = repo.upsert(Feedback(id=None, suggestion_id=suggestion_id, liked=True, comment=None))

    second = repo.upsert(
        Feedback(id=None, suggestion_id=suggestion_id, liked=False, comment="Actually no")
    )

    assert second.id == first.id
    assert second.liked is False
    assert second.comment == "Actually no"
    assert repo.get_by_suggestion(suggestion_id) == second


def test_get_suggestion_returns_none_for_unknown_id(session: Session) -> None:
    assert SuggestionRepository(session).get_suggestion(999) is None


def test_get_suggestion_returns_the_dish(session: Session) -> None:
    suggestion_id = _seed_suggestion(session)

    suggestion = SuggestionRepository(session).get_suggestion(suggestion_id)

    assert suggestion is not None
    assert suggestion.dish_name == "Soup"
