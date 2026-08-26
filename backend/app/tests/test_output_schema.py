import json

from app.agent.output_schema import PlatArgs, PlatIngredient
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
