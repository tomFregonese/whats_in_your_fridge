from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel

from app.domain.fridge_input import FridgeInputMode
from app.domain.suggestion import (
    AgendaEntry,
    AgendaStorage,
    AllergyCheckStatus,
    MealPlan,
    Suggestion,
)


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
    used_stock_item_ids_json: str = "[]"
    fridge_days: int = 3
    freezer_friendly: bool = False
    leftover_of_suggestion_id: int | None = Field(default=None, foreign_key="suggestion.id")
    leftover_transformation: str | None = None

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
            used_stock_item_ids_json=self.used_stock_item_ids_json,
            fridge_days=self.fridge_days,
            freezer_friendly=self.freezer_friendly,
            leftover_of_suggestion_id=self.leftover_of_suggestion_id,
            leftover_transformation=self.leftover_transformation,
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
            used_stock_item_ids_json=suggestion.used_stock_item_ids_json,
            fridge_days=suggestion.fridge_days,
            freezer_friendly=suggestion.freezer_friendly,
            leftover_of_suggestion_id=suggestion.leftover_of_suggestion_id,
            leftover_transformation=suggestion.leftover_transformation,
        )


class AgendaEntryEntity(SQLModel, table=True):
    __tablename__ = "meal_plan_agenda_entry"

    id: int | None = Field(default=None, primary_key=True)
    meal_plan_id: int = Field(foreign_key="meal_plan.id", index=True)
    day_index: int
    suggestion_id: int = Field(foreign_key="suggestion.id")
    storage: str
    warning: str | None = None

    def to_domain(self) -> AgendaEntry:
        return AgendaEntry(
            id=self.id,
            meal_plan_id=self.meal_plan_id,
            day_index=self.day_index,
            suggestion_id=self.suggestion_id,
            storage=AgendaStorage(self.storage),
            warning=self.warning,
        )

    @classmethod
    def from_domain(cls, entry: AgendaEntry) -> AgendaEntryEntity:
        if entry.meal_plan_id is None:
            raise ValueError("AgendaEntry.meal_plan_id must be set before persisting")
        return cls(
            id=entry.id,
            meal_plan_id=entry.meal_plan_id,
            day_index=entry.day_index,
            suggestion_id=entry.suggestion_id,
            storage=entry.storage.value,
            warning=entry.warning,
        )
