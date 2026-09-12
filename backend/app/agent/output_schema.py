"""Pydantic models for the two tools' arguments.

Distinct from `dto/` on purpose: these validate JSON coming from the LLM
(the model's own "API contract" with us), not HTTP request/response
bodies. Also used to generate each tool's JSON schema (`.model_json_schema()`,
see `agent/tools.py`) so the schema the model is told about and the schema
we validate against never drift apart.
"""

from __future__ import annotations

import json

from pydantic import BaseModel, Field, field_validator

from app.domain.dish_idea import DishIdea
from app.domain.suggestion import AllergyCheckStatus, Suggestion


class DemanderPrecisionArgs(BaseModel):
    """Arguments for the `demander_precision` tool."""

    question: str = Field(min_length=1)
    options: list[str] | None = None


class PlatIngredient(BaseModel):
    nom: str = Field(min_length=1)
    quantite: str | None = None
    a_acheter: bool = Field(
        default=False,
        description=(
            "Whether this ingredient is NOT in the fridge/pantry staples and needs to be "
            "bought — a dish may use a handful of these as long as they're flagged."
        ),
    )


class PlatArgs(BaseModel):
    nom: str = Field(min_length=1)
    description: str
    portions: int = Field(gt=0)
    ingredients: list[PlatIngredient] = Field(min_length=1)
    etapes: list[str] = Field(min_length=1)
    ingredients_stock_ids: list[int] = Field(
        default_factory=list,
        description=(
            "IDs (from the `[stock#ID]` tags in the fridge contents) of the persistent "
            "fridge stock items this dish actually used."
        ),
    )
    equipment_used: list[str] = Field(
        default_factory=list,
        description=(
            "Kitchen equipment (beyond a stovetop, pots/pans, knives and basic utensils, "
            "always assumed) this dish actually needs — e.g. 'oven', 'blender'. Never "
            "invent equipment the household hasn't listed as available."
        ),
    )
    fridge_days: int = Field(
        gt=0,
        description=(
            "Estimated number of days this dish safely keeps refrigerated after cooking."
        ),
    )
    freezer_friendly: bool = Field(
        default=False, description="Whether this dish freezes well for later."
    )

    def to_domain(
        self, *, allergy_check_status: AllergyCheckStatus = AllergyCheckStatus.OK
    ) -> Suggestion:
        """Maps to the same `Suggestion` BO the rest of the app already
        uses (Jalon 5's mock, and later milestones' persistence) — the
        agent doesn't invent its own shape for this. `allergy_check_status`
        defaults to `OK`; `agent/loop.py` passes the real, deterministically
        checked status (see `agent/allergy_check.py`) once a dish survives
        (or is corrected past) that check. `ingredients_stock_ids` is
        expected to have already been sanitized against the known stock ids
        for this run (see `agent/stock_reference_check.py`) by the time this
        runs, so it's trusted as-is here. `fridge_days` is expected to have
        already been clamped to a sane range (see
        `agent/conservation_sanity_check.py`) by the time this runs.
        """
        ingredients = [
            {"nom": i.nom, "quantite": i.quantite, "a_acheter": i.a_acheter}
            for i in self.ingredients
        ]
        return Suggestion(
            id=None,
            meal_plan_id=None,
            dish_name=self.nom,
            description=self.description,
            ingredients_json=json.dumps(ingredients),
            steps_json=json.dumps(self.etapes),
            servings=self.portions,
            allergy_check_status=allergy_check_status,
            used_stock_item_ids_json=json.dumps(self.ingredients_stock_ids),
            fridge_days=self.fridge_days,
            freezer_friendly=self.freezer_friendly,
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


class DictatedItemArgs(BaseModel):
    """One grocery item split out of a dictated transcript (see
    `agent/dictation.py`) — a different shape than `FridgeInputItemDtoIn`
    on purpose: `quantity_raw` here always holds the model's own phrasing
    of the amount (e.g. "a couple", "about half a liter"), not a value the
    caller supplied."""

    ingredient_name: str = Field(min_length=1)
    quantity_value: float | None = None
    quantity_unit: str | None = None
    quantity_raw: str | None = None

    @field_validator("quantity_unit", "quantity_raw", mode="before")
    @classmethod
    def _blank_or_stringly_null_becomes_none(cls, value: object) -> object:
        """A small model under grammar-constrained JSON decoding
        occasionally emits the literal string `"null"` (or an empty
        string) for one of these fields instead of the actual JSON
        `null` — the shape is still schema-valid (it's a string, as
        allowed), so nothing upstream catches it. Without this, that
        string would be stored and displayed as if it were real data
        (e.g. a `quantity_unit` of `"null"`)."""
        if isinstance(value, str) and value.strip().lower() in ("", "null", "none"):
            return None
        return value


class EnregistrerIngredientsArgs(BaseModel):
    """Arguments for the `enregistrer_ingredients` tool — the one-shot
    "final answer" contract for parsing a dictated fridge update. No
    `demander_precision` companion here: dictation is a single, best-effort
    pass, not a multi-turn conversation (see `agent/dictation.py`)."""

    items: list[DictatedItemArgs] = Field(default_factory=list)
