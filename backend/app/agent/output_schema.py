"""Pydantic models for the two tools' arguments.

Distinct from `dto/` on purpose: these validate JSON coming from the LLM
(the model's own "API contract" with us), not HTTP request/response
bodies. Also used to generate each tool's JSON schema (`.model_json_schema()`,
see `agent/tools.py`) so the schema the model is told about and the schema
we validate against never drift apart.
"""

from __future__ import annotations

import json

from pydantic import BaseModel, Field

from app.domain.dish_idea import DishIdea
from app.domain.suggestion import AllergyCheckStatus, Suggestion


class DemanderPrecisionArgs(BaseModel):
    """Arguments for the `demander_precision` tool."""

    question: str = Field(min_length=1)
    options: list[str] | None = None


class PlatIngredient(BaseModel):
    nom: str = Field(min_length=1)
    quantite: str | None = None


class PlatArgs(BaseModel):
    nom: str = Field(min_length=1)
    description: str
    portions: int = Field(gt=0)
    ingredients: list[PlatIngredient] = Field(min_length=1)
    etapes: list[str] = Field(min_length=1)

    def to_domain(
        self, *, allergy_check_status: AllergyCheckStatus = AllergyCheckStatus.OK
    ) -> Suggestion:
        """Maps to the same `Suggestion` BO the rest of the app already
        uses (Jalon 5's mock, and later milestones' persistence) — the
        agent doesn't invent its own shape for this. `allergy_check_status`
        defaults to `OK`; `agent/loop.py` passes the real, deterministically
        checked status (see `agent/allergy_check.py`) once a dish survives
        (or is corrected past) that check.
        """
        ingredient_strings = [
            f"{i.nom} ({i.quantite})" if i.quantite else i.nom for i in self.ingredients
        ]
        return Suggestion(
            id=None,
            meal_plan_id=None,
            dish_name=self.nom,
            description=self.description,
            ingredients_json=json.dumps(ingredient_strings),
            steps_json=json.dumps(self.etapes),
            servings=self.portions,
            allergy_check_status=allergy_check_status,
        )


class ProposerPlatsArgs(BaseModel):
    """Arguments for the `proposer_plats` tool — the "final answer" contract
    of the `RECIPES` phase."""

    plats: list[PlatArgs] = Field(min_length=1)
    notes_generales: str | None = None


class IdeeArgs(BaseModel):
    """One dish idea — name and a one-line description only, deliberately
    without ingredients or steps (those only exist once `ProposerPlatsArgs`
    is generated for whichever idea(s) the user picks)."""

    nom: str = Field(min_length=1)
    description: str

    def to_domain(self) -> DishIdea:
        return DishIdea(dish_name=self.nom, description=self.description)


class ProposerIdeesArgs(BaseModel):
    """Arguments for the `proposer_idees` tool — the "final answer" contract
    of the `IDEAS` phase."""

    idees: list[IdeeArgs] = Field(min_length=1)
    notes_generales: str | None = None
