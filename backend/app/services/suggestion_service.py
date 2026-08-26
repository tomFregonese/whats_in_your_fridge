"""Generates meal suggestions from a fridge input.

V1 milestone 5: returns a fixed set of mocked dishes so the full UI
round-trip (submit → persist → display) can be validated before the real
OpenRouter agent is wired in (a later milestone). The `Suggestion` BOs
below are the exact same shape the real agent will eventually produce —
only *how* they're obtained changes, not their shape or the DTOs built on
top of them.
"""

from app.domain.fridge_input import FridgeInput
from app.domain.suggestion import AllergyCheckStatus, Suggestion
from app.persistence.repositories.fridge_input_repository import FridgeInputRepository

_MOCK_SUGGESTIONS = [
    Suggestion(
        id=None,
        meal_plan_id=None,
        dish_name="Skillet chicken with roasted vegetables",
        description="A simple one-pan dinner using whatever's in the fridge.",
        ingredients_json='["chicken breast", "bell pepper", "onion", "olive oil", "garlic"]',
        steps_json=(
            '["Chop the vegetables.", "Sear the chicken.", '
            '"Roast everything together for 20 minutes."]'
        ),
        servings=4,
        allergy_check_status=AllergyCheckStatus.OK,
    ),
    Suggestion(
        id=None,
        meal_plan_id=None,
        dish_name="Vegetable fried rice",
        description="A quick way to use up leftover rice and any vegetables.",
        ingredients_json='["rice", "carrot", "peas", "soy sauce", "egg"]',
        steps_json=(
            '["Scramble the egg.", "Stir-fry the vegetables.", '
            '"Add rice and soy sauce, toss together."]'
        ),
        servings=4,
        allergy_check_status=AllergyCheckStatus.OK,
    ),
    Suggestion(
        id=None,
        meal_plan_id=None,
        dish_name="Tomato and lentil soup",
        description="A warming batch-cook soup that keeps well in the fridge.",
        ingredients_json='["tomato", "red lentils", "onion", "vegetable stock", "cumin"]',
        steps_json=(
            '["Cook the onion until soft.", "Add lentils, tomato and stock.", '
            '"Simmer for 25 minutes."]'
        ),
        servings=4,
        allergy_check_status=AllergyCheckStatus.OK,
    ),
]


class SuggestionService:
    def __init__(self, fridge_input_repository: FridgeInputRepository) -> None:
        self._fridge_input_repository = fridge_input_repository

    def generate(self, fridge_input: FridgeInput) -> tuple[FridgeInput, list[Suggestion]]:
        saved = self._fridge_input_repository.add(fridge_input)
        return saved, _MOCK_SUGGESTIONS
