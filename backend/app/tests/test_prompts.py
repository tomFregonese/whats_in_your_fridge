from datetime import UTC, datetime

from app.agent import prompts
from app.domain.allergy import Allergy
from app.domain.fridge_input import FridgeInput, FridgeInputItem, FridgeInputMode
from app.domain.preference_note import PreferenceNote, PreferenceSource


def test_system_prompt_includes_servings_and_pantry_staples() -> None:
    prompt = prompts.build_system_prompt(default_servings=4, allergies=[], preferences=[])

    assert "4" in prompt
    assert "salt" in prompt
    assert "proposer_plats" in prompt
    assert "demander_precision" in prompt


def test_system_prompt_includes_allergies_when_present() -> None:
    allergies = [Allergy(id=1, ingredient_name="peanut", notes=None)]

    prompt = prompts.build_system_prompt(default_servings=4, allergies=allergies, preferences=[])

    assert "peanut" in prompt
    assert "STRICT ALLERGIES" in prompt


def test_system_prompt_omits_allergy_section_when_none() -> None:
    prompt = prompts.build_system_prompt(default_servings=4, allergies=[], preferences=[])

    assert "STRICT ALLERGIES" not in prompt


def test_system_prompt_includes_dedup_context_when_present() -> None:
    prompt = prompts.build_system_prompt(
        default_servings=4,
        allergies=[],
        preferences=[],
        dedup_context='Recently suggested dishes to avoid repeating: "Carrot soup".',
    )

    assert "Carrot soup" in prompt


def test_system_prompt_omits_dedup_section_when_empty() -> None:
    prompt = prompts.build_system_prompt(
        default_servings=4, allergies=[], preferences=[], dedup_context=""
    )

    assert "Recently suggested" not in prompt


def test_system_prompt_includes_preferences_when_present() -> None:
    preferences = [
        PreferenceNote(
            id=1,
            content="loves spicy food",
            source=PreferenceSource.MANUAL,
            created_at=datetime.now(UTC),
        )
    ]

    prompt = prompts.build_system_prompt(default_servings=4, allergies=[], preferences=preferences)

    assert "loves spicy food" in prompt


def test_user_message_includes_structured_items() -> None:
    fridge_input = FridgeInput(
        id=1,
        mode=FridgeInputMode.BATCH,
        free_text=None,
        created_at=datetime.now(UTC),
        items=[
            FridgeInputItem(
                id=1,
                fridge_input_id=1,
                ingredient_name="carrot",
                quantity_value=3,
                quantity_unit="pcs",
                quantity_raw=None,
            )
        ],
    )

    message = prompts.build_user_message(fridge_input)

    assert "batch" in message
    assert "carrot" in message
    assert "3" in message


def test_user_message_includes_free_text() -> None:
    fridge_input = FridgeInput(
        id=1,
        mode=FridgeInputMode.SINGLE,
        free_text="half a lemon and some rice",
        created_at=datetime.now(UTC),
    )

    message = prompts.build_user_message(fridge_input)

    assert "half a lemon and some rice" in message
