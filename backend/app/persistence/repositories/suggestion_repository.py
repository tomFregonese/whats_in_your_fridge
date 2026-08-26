from dataclasses import replace

from sqlalchemy import ColumnElement, desc
from sqlmodel import Session, select

from app.domain.suggestion import MealPlan, Suggestion
from app.persistence.entities.suggestion_entity import MealPlanEntity, SuggestionEntity


class SuggestionRepository:
    """Owns both `meal_plan` and `suggestion` rows — `MealPlan` is the
    aggregate root, `Suggestion` its children, same convention as
    `FridgeInputRepository`/`FridgeInput.items`.

    Written to by `SuggestionService` right after a generation completes;
    read by `MealPlanService` (`GET /api/meal-plans` history,
    `GET /api/meal-plans/{id}` WeekPlan/SingleDish detail) and by
    `list_recent_dish_names` for `agent/dedup.py`'s exclusion context.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, meal_plan: MealPlan) -> MealPlan:
        """Persists the parent row, then each suggestion against its real
        id — the same aggregate-assembly convention as
        `FridgeInputRepository.add()`.
        """
        entity = MealPlanEntity.from_domain(meal_plan)
        self._session.add(entity)
        self._session.flush()  # assigns entity.id without committing yet
        assert entity.id is not None

        suggestion_entities = [
            SuggestionEntity.from_domain(replace(suggestion, meal_plan_id=entity.id))
            for suggestion in meal_plan.suggestions
        ]
        for suggestion_entity in suggestion_entities:
            self._session.add(suggestion_entity)

        self._session.commit()
        self._session.refresh(entity)
        for suggestion_entity in suggestion_entities:
            self._session.refresh(suggestion_entity)

        result = entity.to_domain()
        result.suggestions = [s.to_domain() for s in suggestion_entities]
        return result

    def get(self, meal_plan_id: int) -> MealPlan | None:
        entity = self._session.get(MealPlanEntity, meal_plan_id)
        if entity is None:
            return None
        result = entity.to_domain()
        result.suggestions = self._load_suggestions(meal_plan_id)
        return result

    def get_suggestion(self, suggestion_id: int) -> Suggestion | None:
        """A single dish, independent of its parent plan — used by
        `FeedbackService` to validate a `suggestion_id` and to attribute a
        feedback comment to its dish name.
        """
        entity = self._session.get(SuggestionEntity, suggestion_id)
        return entity.to_domain() if entity is not None else None

    def list_all(self) -> list[MealPlan]:
        """Most recent first — the order `MealPlanHistory` renders in."""
        # SQLModel types a class-level field access as its plain Python
        # type rather than a column construct — same known gap noted below.
        order: ColumnElement[bool] = desc(MealPlanEntity.created_at)  # type: ignore[arg-type]
        entities = self._session.exec(select(MealPlanEntity).order_by(order)).all()

        results = []
        for entity in entities:
            assert entity.id is not None
            meal_plan = entity.to_domain()
            meal_plan.suggestions = self._load_suggestions(entity.id)
            results.append(meal_plan)
        return results

    def _load_suggestions(self, meal_plan_id: int) -> list[Suggestion]:
        condition: ColumnElement[bool] = (
            SuggestionEntity.meal_plan_id == meal_plan_id  # type: ignore[assignment]
        )
        entities = self._session.exec(select(SuggestionEntity).where(condition)).all()
        return [entity.to_domain() for entity in entities]

    def list_recent_dish_names(self, limit: int) -> list[str]:
        """Most recently *planned* dishes first (ordered by the parent
        `meal_plan.created_at`, not `suggestion`'s own id — a plan's
        dishes should all count as equally "recent"). May contain
        duplicate names; callers that want a unique exclusion list
        de-duplicate themselves (see `agent/dedup.py`).
        """
        order: ColumnElement[bool] = desc(MealPlanEntity.created_at)  # type: ignore[arg-type]
        join_condition: ColumnElement[bool] = (
            SuggestionEntity.meal_plan_id == MealPlanEntity.id  # type: ignore[assignment]
        )
        statement = (
            select(SuggestionEntity.dish_name)
            .join(MealPlanEntity, join_condition)
            .order_by(order)
            .limit(limit)
        )
        return list(self._session.exec(statement).all())
