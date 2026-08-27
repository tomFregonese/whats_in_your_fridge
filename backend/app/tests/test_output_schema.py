import json

import pytest
from pydantic import ValidationError

from app.agent.output_schema import IdeeArgs, PlatArgs, PlatIngredient, ProposerIdeesArgs
from app.domain.suggestion import AllergyCheckStatus


def test_plat_args_to_domain_formats_ingredients_with_quantity() -> None:
    plat = PlatArgs(
        nom="Carrot soup",
        description="Simple soup",
        portions=4,
        ingredients=[
            PlatIngredient(nom="carrot", quantite="3"),
            PlatIngredient(nom="salt", quantite=None),
        ],
        etapes=["Boil.", "Blend."],
    )

    suggestion = plat.to_domain()

    assert suggestion.dish_name == "Carrot soup"
    assert suggestion.servings == 4
    assert suggestion.allergy_check_status == AllergyCheckStatus.OK
    assert json.loads(suggestion.ingredients_json) == ["carrot (3)", "salt"]
    assert json.loads(suggestion.steps_json) == ["Boil.", "Blend."]


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
