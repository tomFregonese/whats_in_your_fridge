from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field

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
    """One flat Dto covers both outcomes rather than a tagged union — the
    frontend only ever needs to branch on `status`, and the fields that
    don't apply to a given status are simply left at their defaults.

    `model_unavailable` (a later milestone, model-availability check) and
    `vault_locked` (already live — see `VaultLockedError`, surfaced as a
    plain HTTP 423 rather than folded into this success-shaped Dto) are
    intentionally not status values here — those are real failures, not
    part of the normal conversation flow the way a clarifying question is.
    """

    status: Literal["completed", "clarification_needed"]
    fridge_input_id: int
    suggestions: list[SuggestionDtoOut] = Field(default_factory=list)
    notes_generales: str | None = None
    run_id: int | None = None
    question: str | None = None
    options: list[str] | None = None


class RespondDtoIn(BaseModel):
    answer: str = Field(min_length=1)
