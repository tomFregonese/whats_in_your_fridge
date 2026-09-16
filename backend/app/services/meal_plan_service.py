"""Read access to persisted meal plans, plus the one user-facing edit the
table view needs.

`SuggestionService` (agent orchestration) is the only writer of a whole
`MealPlan`/`Suggestion` aggregate — this service is what
`GET /api/meal-plans` (MealPlanHistory), `GET /api/meal-plans/{id}`
(WeekPlan/SingleDish detail), and `PATCH /api/suggestions/{id}` (the
meal-plan table's inline edit) go through. It never touches agent
orchestration state (`agent_run`), only the already-persisted result.
"""

from app.domain.suggestion import MealPlan, Suggestion
from app.persistence.repositories.suggestion_repository import SuggestionRepository
from app.services.exceptions import NotFoundError


class MealPlanService:
    def __init__(self, repository: SuggestionRepository) -> None:
        self._repository = repository

    def list_all(self) -> list[MealPlan]:
        return self._repository.list_all()

    def get(self, meal_plan_id: int) -> MealPlan:
        meal_plan = self._repository.get(meal_plan_id)
        if meal_plan is None:
            raise NotFoundError(f"Meal plan {meal_plan_id} does not exist.")
        return meal_plan

    def update_suggestion(
        self,
        suggestion_id: int,
        *,
        dish_name: str,
        servings: int,
        leftover_transformation: str | None,
    ) -> Suggestion:
        suggestion = self._repository.update(
            suggestion_id,
            dish_name=dish_name,
            servings=servings,
            leftover_transformation=leftover_transformation,
        )
        if suggestion is None:
            raise NotFoundError(f"Suggestion {suggestion_id} does not exist.")
        return suggestion
