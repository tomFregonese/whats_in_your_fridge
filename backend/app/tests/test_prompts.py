from datetime import UTC, datetime

import pytest

from app.agent import prompts
from app.domain.agent_run import AgentRunPhase
from app.domain.allergy import Allergy
from app.domain.dish_idea import DishIdea
from app.domain.equipment import Equipment
from app.domain.fridge_input import FridgeInput, FridgeInputItem, FridgeInputMode, SourcingMode
from app.domain.preference_note import PreferenceNote, PreferenceSource


def test_system_prompt_includes_servings_and_pantry_staples() -> None:
    prompt = prompts.build_system_prompt(
        default_servings=4,
        allergies=[],
        equipment=[],
        preferences=[],
        sourcing_mode=SourcingMode.FRIDGE_PLUS_SHOPPING,
        phase=AgentRunPhase.RECIPES,
    )

    assert "4" in prompt
    assert "salt" in prompt
    assert "proposer_plats" in prompt
    assert "demander_precision" in prompt


def test_system_prompt_includes_allergies_when_present() -> None:
    allergies = [Allergy(id=1, ingredient_name="peanut", notes=None)]

    prompt = prompts.build_system_prompt(
        default_servings=4,
        allergies=allergies,
        equipment=[],
        preferences=[],
        sourcing_mode=SourcingMode.FRIDGE_PLUS_SHOPPING,
        phase=AgentRunPhase.RECIPES,
    )

    assert "peanut" in prompt
    assert "STRICT ALLERGIES" in prompt


def test_system_prompt_omits_allergy_section_when_none() -> None:
    prompt = prompts.build_system_prompt(
        default_servings=4,
        allergies=[],
        equipment=[],
        preferences=[],
        sourcing_mode=SourcingMode.FRIDGE_PLUS_SHOPPING,
        phase=AgentRunPhase.RECIPES,
    )

    assert "STRICT ALLERGIES" not in prompt


def test_system_prompt_includes_equipment_when_present() -> None:
    equipment = [Equipment(id=1, name="oven")]

    prompt = prompts.build_system_prompt(
        default_servings=4,
        allergies=[],
        equipment=equipment,
        preferences=[],
        sourcing_mode=SourcingMode.FRIDGE_PLUS_SHOPPING,
        phase=AgentRunPhase.RECIPES,
    )

    assert "oven" in prompt


def test_system_prompt_forbids_extra_equipment_when_none_listed() -> None:
    prompt = prompts.build_system_prompt(
        default_servings=4,
        allergies=[],
        equipment=[],
        preferences=[],
        sourcing_mode=SourcingMode.FRIDGE_PLUS_SHOPPING,
        phase=AgentRunPhase.RECIPES,
    )

    assert "No additional equipment" in prompt


def test_system_prompt_includes_dedup_context_when_present() -> None:
    prompt = prompts.build_system_prompt(
        default_servings=4,
        allergies=[],
        equipment=[],
        preferences=[],
        sourcing_mode=SourcingMode.FRIDGE_PLUS_SHOPPING,
        phase=AgentRunPhase.RECIPES,
        dedup_context='Recently suggested dishes to avoid repeating: "Carrot soup".',
    )

    assert "Carrot soup" in prompt


def test_system_prompt_omits_dedup_section_when_empty() -> None:
    prompt = prompts.build_system_prompt(
        default_servings=4,
        allergies=[],
        equipment=[],
        preferences=[],
        sourcing_mode=SourcingMode.FRIDGE_PLUS_SHOPPING,
        phase=AgentRunPhase.RECIPES,
        dedup_context="",
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

    prompt = prompts.build_system_prompt(
        default_servings=4,
        allergies=[],
        equipment=[],
        preferences=preferences,
        sourcing_mode=SourcingMode.FRIDGE_PLUS_SHOPPING,
        phase=AgentRunPhase.RECIPES,
    )

    assert "loves spicy food" in prompt


# --- Sourcing mode instructions ---


def test_fridge_only_forbids_buying_anything() -> None:
    prompt = prompts.build_system_prompt(
        default_servings=4,
        allergies=[],
        equipment=[],
        preferences=[],
        sourcing_mode=SourcingMode.FRIDGE_ONLY,
        phase=AgentRunPhase.RECIPES,
    )

    assert "never set `a_acheter` to true" in prompt
    assert "never include an ingredient that would need to be bought" in prompt


def test_fridge_plus_shopping_allows_a_few_extras() -> None:
    prompt = prompts.build_system_prompt(
        default_servings=4,
        allergies=[],
        equipment=[],
        preferences=[],
        sourcing_mode=SourcingMode.FRIDGE_PLUS_SHOPPING,
        phase=AgentRunPhase.RECIPES,
    )

    assert "a few ingredients" in prompt
    assert "a_acheter" in prompt


def test_shopping_only_does_not_limit_ideas_to_the_fridge() -> None:
    prompt = prompts.build_system_prompt(
        default_servings=4,
        allergies=[],
        equipment=[],
        preferences=[],
        sourcing_mode=SourcingMode.SHOPPING_ONLY,
        phase=AgentRunPhase.RECIPES,
    )

    assert "don't limit dish ideas to the fridge contents" in prompt
    assert "planning a shopping trip" in prompt


def test_sourcing_mode_wording_differs_across_all_three_modes() -> None:
    prompts_by_mode = {
        mode: prompts.build_system_prompt(
            default_servings=4,
            allergies=[],
            equipment=[],
            preferences=[],
            sourcing_mode=mode,
            phase=AgentRunPhase.RECIPES,
        )
        for mode in SourcingMode
    }

    assert len({p for p in prompts_by_mode.values()}) == len(SourcingMode)


# --- Phase-specific instructions ---


def test_ideas_phase_instructs_proposer_idees_not_proposer_plats() -> None:
    prompt = prompts.build_system_prompt(
        default_servings=4,
        allergies=[],
        equipment=[],
        preferences=[],
        sourcing_mode=SourcingMode.FRIDGE_PLUS_SHOPPING,
        phase=AgentRunPhase.IDEAS,
        mode=FridgeInputMode.BATCH,
        days=5,
    )

    assert "proposer_idees" in prompt
    assert "proposer_plats" not in prompt


def test_recipes_phase_instructs_proposer_plats_not_proposer_idees() -> None:
    prompt = prompts.build_system_prompt(
        default_servings=4,
        allergies=[],
        equipment=[],
        preferences=[],
        sourcing_mode=SourcingMode.FRIDGE_PLUS_SHOPPING,
        phase=AgentRunPhase.RECIPES,
    )

    assert "proposer_plats" in prompt
    assert "proposer_idees" not in prompt


def test_ideas_phase_requires_mode() -> None:
    with pytest.raises(ValueError):
        prompts.build_system_prompt(
            default_servings=4,
            allergies=[],
            equipment=[],
            preferences=[],
            sourcing_mode=SourcingMode.FRIDGE_PLUS_SHOPPING,
            phase=AgentRunPhase.IDEAS,
        )


def test_ideas_phase_hint_varies_by_mode() -> None:
    batch_prompt = prompts.build_system_prompt(
        default_servings=4,
        allergies=[],
        equipment=[],
        preferences=[],
        sourcing_mode=SourcingMode.FRIDGE_PLUS_SHOPPING,
        phase=AgentRunPhase.IDEAS,
        mode=FridgeInputMode.BATCH,
    )
    single_prompt = prompts.build_system_prompt(
        default_servings=4,
        allergies=[],
        equipment=[],
        preferences=[],
        sourcing_mode=SourcingMode.FRIDGE_PLUS_SHOPPING,
        phase=AgentRunPhase.IDEAS,
        mode=FridgeInputMode.SINGLE,
    )

    assert batch_prompt != single_prompt
    assert "week" in batch_prompt
    assert "single meal" in single_prompt


def test_ideas_phase_batch_hint_mentions_days_and_reuse() -> None:
    prompt = prompts.build_system_prompt(
        default_servings=4,
        allergies=[],
        equipment=[],
        preferences=[],
        sourcing_mode=SourcingMode.FRIDGE_PLUS_SHOPPING,
        phase=AgentRunPhase.IDEAS,
        mode=FridgeInputMode.BATCH,
        days=5,
    )

    assert "5 day(s)" in prompt
    assert "pasta" in prompt.lower()


def test_recipes_phase_instructs_equipment_and_conservation_fields() -> None:
    prompt = prompts.build_system_prompt(
        default_servings=4,
        allergies=[],
        equipment=[],
        preferences=[],
        sourcing_mode=SourcingMode.FRIDGE_PLUS_SHOPPING,
        phase=AgentRunPhase.RECIPES,
    )

    assert "equipment_used" in prompt
    assert "fridge_days" in prompt
    assert "freezer_friendly" in prompt
    assert "a_acheter" in prompt


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


def test_ideas_phase_batch_hint_requires_restes_de_field() -> None:
    prompt = prompts.build_system_prompt(
        default_servings=4,
        allergies=[],
        equipment=[],
        preferences=[],
        sourcing_mode=SourcingMode.FRIDGE_PLUS_SHOPPING,
        phase=AgentRunPhase.IDEAS,
        mode=FridgeInputMode.BATCH,
        days=5,
    )

    assert "restes_de" in prompt
    assert "NEVER" in prompt


# --- build_selection_message ---


def test_build_selection_message_names_every_selected_dish() -> None:
    selected = [
        DishIdea(dish_name="Carrot soup", description="Simple soup"),
        DishIdea(dish_name="Tomato soup", description="Another soup"),
    ]

    message = prompts.build_selection_message(selected)

    assert '"Carrot soup"' in message
    assert '"Tomato soup"' in message
    assert "proposer_plats" in message


def test_build_selection_message_restates_the_leftover_link() -> None:
    selected = [
        DishIdea(dish_name="Pasta", description="Big batch"),
        DishIdea(
            dish_name="Pasta gratin",
            description="Baked leftovers",
            leftover_of_dish_name="Pasta",
            transformation_note="Baked with cheese",
        ),
    ]

    message = prompts.build_selection_message(selected)

    assert 'reuses the leftovers of "Pasta"' in message
    assert "Baked with cheese" in message
    assert "restes_de" in message


def test_user_message_includes_free_text() -> None:
    fridge_input = FridgeInput(
        id=1,
        mode=FridgeInputMode.SINGLE,
        free_text="half a lemon and some rice",
        created_at=datetime.now(UTC),
    )

    message = prompts.build_user_message(fridge_input)

    assert "half a lemon and some rice" in message
