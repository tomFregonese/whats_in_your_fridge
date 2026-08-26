from sqlalchemy import ColumnElement, desc
from sqlmodel import Session, select

from app.persistence.entities.suggestion_entity import MealPlanEntity, SuggestionEntity


class SuggestionRepository:
    """Read-only for now: nothing writes `meal_plan`/`suggestion` rows yet
    (the agent loop returns results without persisting them until a later
    milestone — see the project plan). This exists early so `agent/dedup.py`
    has a real table to query against and starts working automatically
    the moment persistence lands, with no further glue code.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_recent_dish_names(self, limit: int) -> list[str]:
        """Most recently *planned* dishes first (ordered by the parent
        `meal_plan.created_at`, not `suggestion`'s own id — a plan's
        dishes should all count as equally "recent"). May contain
        duplicate names; callers that want a unique exclusion list
        de-duplicate themselves (see `agent/dedup.py`).
        """
        # SQLModel types a class-level field access as its plain Python
        # type rather than a column construct — same known gap noted in
        # PreferenceNoteRepository.
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
