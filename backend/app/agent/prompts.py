"""System/user prompt construction for the agent loop.

Household context: portions, allergies, preferences, fridge contents, and
(since milestone 9) a recent-meals dedup context — see `agent/dedup.py`.
The allergy list below is informational context for the model only; the
deterministic code-level check that actually enforces it lives in
`agent/allergy_check.py`.
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
    dedup_context: str = "",
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

    if dedup_context:
        lines.append(dedup_context)

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
