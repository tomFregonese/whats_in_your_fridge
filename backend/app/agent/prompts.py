"""System/user prompt construction for the agent loop.

Milestone 7 scope: household context (portions, allergies, preferences,
fridge contents). Recent-meal variety context is added by `dedup.py` in a
later milestone (see the project plan) — not referenced here yet, and the
allergy list below is informational context for the model only; the
deterministic code-level check that actually enforces it is wired in by
another later milestone too.
"""

from app.domain.allergy import Allergy
from app.domain.fridge_input import FridgeInput, FridgeInputItem
from app.domain.preference_note import PreferenceNote

PANTRY_STAPLES = "salt, pepper, cooking oil, water"


def build_system_prompt(
    *,
    default_servings: int,
    allergies: list[Allergy],
    preferences: list[PreferenceNote],
) -> str:
    lines = [
        "You are a batch-cooking assistant for a self-hosted household app. "
        "Suggest dishes to cook from what's in the fridge.",
        f"Default number of servings, unless the user says otherwise: {default_servings}.",
        f"Assume these pantry staples are always available: {PANTRY_STAPLES}.",
    ]

    if allergies:
        names = ", ".join(allergy.ingredient_name for allergy in allergies)
        lines.append(
            "STRICT ALLERGIES — never include these ingredients or their direct "
            f"derivatives in any dish, under any circumstance: {names}."
        )

    if preferences:
        notes = "; ".join(preference.content for preference in preferences)
        lines.append(f"Known preferences from this household: {notes}.")

    lines.append(
        "Every final answer must go through the `proposer_plats` tool. If the fridge "
        "contents or the request are ambiguous, call `demander_precision` instead of "
        "guessing — never answer with plain text."
    )

    return "\n".join(lines)


def build_user_message(fridge_input: FridgeInput) -> str:
    parts = [f"Mode: {fridge_input.mode.value}."]

    if fridge_input.items:
        item_lines = [f"- {_format_item(item)}" for item in fridge_input.items]
        parts.append("Fridge contents:\n" + "\n".join(item_lines))

    if fridge_input.free_text:
        parts.append(f"Additional notes from the user: {fridge_input.free_text}")

    return "\n\n".join(parts)


def _format_item(item: FridgeInputItem) -> str:
    quantity = item.quantity_raw
    if quantity is None and item.quantity_value is not None:
        quantity = f"{item.quantity_value} {item.quantity_unit or ''}".strip()
    return f"{item.ingredient_name} ({quantity})" if quantity else item.ingredient_name
