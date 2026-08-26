"""Read access to persisted meal plans.

`SuggestionService` (agent orchestration) is the only writer — this
service is what `GET /api/meal-plans` (MealPlanHistory) and
`GET /api/meal-plans/{id}` (WeekPlan/SingleDish detail) read through.
"""

from app.domain.suggestion import MealPlan
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
