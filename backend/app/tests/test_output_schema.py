import json

import pytest
from pydantic import ValidationError

from app.agent.output_schema import (
    DictatedItemArgs,
    IdeeArgs,
    PlatArgs,
    PlatIngredient,
    ProposerIdeesArgs,
)
from app.domain.suggestion import AllergyCheckStatus


def test_plat_args_to_domain_formats_ingredients_with_quantity() -> None:
    plat = PlatArgs(
        nom="Carrot soup",
        description="Simple soup",
        portions=4,
        ingredients=[
            PlatIngredient(nom="carrot", quantite="3"),
            PlatIngredient(nom="salt", quantite=None, a_acheter=True),
        ],
        etapes=["Boil.", "Blend."],
        fridge_days=4,
        freezer_friendly=True,
    )

    suggestion = plat.to_domain()

    assert suggestion.dish_name == "Carrot soup"
    assert suggestion.servings == 4
    assert suggestion.allergy_check_status == AllergyCheckStatus.OK
    assert json.loads(suggestion.ingredients_json) == [
        {"nom": "carrot", "quantite": "3", "a_acheter": False},
        {"nom": "salt", "quantite": None, "a_acheter": True},
    ]
    assert json.loads(suggestion.steps_json) == ["Boil.", "Blend."]
    assert suggestion.fridge_days == 4
    assert suggestion.freezer_friendly is True


def test_idee_args_to_domain() -> None:
    idee = IdeeArgs(nom="Carrot soup", description="Simple soup")

    dish_idea = idee.to_domain()

    assert dish_idea.dish_name == "Carrot soup"
    assert dish_idea.description == "Simple soup"


def test_proposer_idees_args_requires_at_least_one_idee() -> None:
    parsed = ProposerIdeesArgs.model_validate(
        {
            "idees": [{"nom": "Carrot soup", "description": "Simple soup"}],
            "notes_generales": None,
        }
    )

    assert len(parsed.idees) == 1

    with pytest.raises(ValidationError):
        ProposerIdeesArgs.model_validate({"idees": [], "notes_generales": None})


@pytest.mark.parametrize("literal", ["null", "NULL", "None", "", "  "])
def test_dictated_item_args_treats_stringly_null_as_none(literal: str) -> None:
    # Regression test: under grammar-constrained JSON decoding, a small
    # model occasionally emits the literal string "null" (schema-valid —
    # it's a string, as allowed) instead of the JSON `null` for one of
    # these optional fields.
    item = DictatedItemArgs(
        ingredient_name="carrot", quantity_value=3, quantity_unit=literal, quantity_raw=literal
    )

    assert item.quantity_unit is None
    assert item.quantity_raw is None


def test_dictated_item_args_keeps_a_real_unit() -> None:
    item = DictatedItemArgs(
        ingredient_name="carrot", quantity_value=3, quantity_unit="kg", quantity_raw=None
    )

    assert item.quantity_unit == "kg"
