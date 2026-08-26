from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel

from app.domain.suggestion import Suggestion


class SuggestionDtoOut(BaseModel):
    dish_name: str
    description: str
    ingredients: list[str]
    steps: list[str]
    servings: int

    @classmethod
    def from_domain(cls, suggestion: Suggestion) -> SuggestionDtoOut:
        return cls(
            dish_name=suggestion.dish_name,
            description=suggestion.description,
            ingredients=json.loads(suggestion.ingredients_json),
            steps=json.loads(suggestion.steps_json),
            servings=suggestion.servings,
        )


class SuggestionsResultDtoOut(BaseModel):
    """`status` is a `Literal` with a single member today on purpose: the
    real agent (a later milestone) adds `clarification_needed`,
    `model_unavailable`, `vault_locked` as siblings, matching the project
    plan's documented response contract for this endpoint.
    """

    status: Literal["completed"]
    fridge_input_id: int
    suggestions: list[SuggestionDtoOut]
