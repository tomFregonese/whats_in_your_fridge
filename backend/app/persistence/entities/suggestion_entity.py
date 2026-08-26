from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel

from app.domain.fridge_input import FridgeInputMode
from app.domain.suggestion import AllergyCheckStatus, MealPlan, Suggestion


class MealPlanEntity(SQLModel, table=True):
    __tablename__ = "meal_plan"

    id: int | None = Field(default=None, primary_key=True)
    fridge_input_id: int = Field(foreign_key="fridge_input.id", index=True)
    mode: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)

    def to_domain(self) -> MealPlan:
        """Maps this row only — `suggestions` stays empty here, populated
        by the repository instead. See `MealPlan`'s docstring.
        """
        return MealPlan(
            id=self.id,
            fridge_input_id=self.fridge_input_id,
            mode=FridgeInputMode(self.mode),
            created_at=self.created_at,
        )

    @classmethod
    def from_domain(cls, meal_plan: MealPlan) -> MealPlanEntity:
        return cls(
            id=meal_plan.id,
            fridge_input_id=meal_plan.fridge_input_id,
            mode=meal_plan.mode.value,
            created_at=meal_plan.created_at,
        )


class SuggestionEntity(SQLModel, table=True):
    __tablename__ = "suggestion"

    id: int | None = Field(default=None, primary_key=True)
    meal_plan_id: int = Field(foreign_key="meal_plan.id", index=True)
    dish_name: str
    description: str
    ingredients_json: str
    steps_json: str
    servings: int
    allergy_check_status: str

    def to_domain(self) -> Suggestion:
        return Suggestion(
            id=self.id,
            meal_plan_id=self.meal_plan_id,
            dish_name=self.dish_name,
            description=self.description,
            ingredients_json=self.ingredients_json,
            steps_json=self.steps_json,
            servings=self.servings,
            allergy_check_status=AllergyCheckStatus(self.allergy_check_status),
        )

    @classmethod
    def from_domain(cls, suggestion: Suggestion) -> SuggestionEntity:
        if suggestion.meal_plan_id is None:
            raise ValueError("Suggestion.meal_plan_id must be set before persisting")
        return cls(
            id=suggestion.id,
            meal_plan_id=suggestion.meal_plan_id,
            dish_name=suggestion.dish_name,
            description=suggestion.description,
            ingredients_json=suggestion.ingredients_json,
            steps_json=suggestion.steps_json,
            servings=suggestion.servings,
            allergy_check_status=suggestion.allergy_check_status.value,
        )
