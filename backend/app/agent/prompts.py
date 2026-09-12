"""System/user prompt construction for the agent loop.

Household context: portions, allergies, preferences, fridge contents, and
(since milestone 9) a recent-meals dedup context — see `agent/dedup.py`.
The allergy list below is informational context for the model only; the
deterministic code-level check that actually enforces it lives in
`agent/allergy_check.py`.

The closing instruction is phase-specific (see `AgentRunPhase`): the
`IDEAS` phase asks for a shortlist of names + descriptions only, sized by
`mode`; the `RECIPES` phase asks for the full recipe of exactly whichever
idea(s) the user picked — those picks travel as the preceding tool-result
message (built by `services/suggestion_service.py`), not through this
system prompt.
"""

from app.domain.agent_run import AgentRunPhase
from app.domain.allergy import Allergy
from app.domain.equipment import Equipment
from app.domain.fridge_input import FridgeInput, FridgeInputItem, FridgeInputMode
from app.domain.preference_note import PreferenceNote

PANTRY_STAPLES = "salt, pepper, cooking oil, water"

# Always assumed available, on the same footing as `PANTRY_STAPLES` — the
# household's `equipment` list (see `app.domain.equipment.Equipment`) only
# needs to cover appliances beyond this (oven, microwave, blender, ...),
# never this baseline. Kept in sync with `agent/equipment_check.py`'s
# docstring.
BASE_EQUIPMENT = "a stovetop/hob, pots and pans, knives, a cutting board, mixing bowls"


def build_system_prompt(
    *,
    default_servings: int,
    allergies: list[Allergy],
    equipment: list[Equipment],
    preferences: list[PreferenceNote],
    phase: AgentRunPhase,
    mode: FridgeInputMode | None = None,
    days: int | None = None,
    dedup_context: str = "",
) -> str:
    if phase == AgentRunPhase.IDEAS and mode is None:
        raise ValueError("`mode` is required to size the idea shortlist in the IDEAS phase.")

    lines = [
        "You are a batch-cooking assistant for a self-hosted household app. "
        "Suggest dishes to cook primarily from what's in the fridge — a few ingredients "
        "the household doesn't have are fine as long as they're clearly flagged (see "
        "`a_acheter` below) so they end up on a shopping list, rather than silently "
        "assumed available.",
        f"Default number of servings, unless the user says otherwise: {default_servings}.",
        f"Assume these pantry staples are always available: {PANTRY_STAPLES}.",
        f"Assume this equipment is always available: {BASE_EQUIPMENT}.",
    ]

    if equipment:
        names = ", ".join(item.name for item in equipment)
        lines.append(
            "Additional equipment available at this household: "
            f"{names}. Only propose dishes that can be fully cooked with this equipment "
            "plus the baseline above — never assume an oven, microwave, blender, or any "
            "other appliance that isn't listed here."
        )
    else:
        lines.append(
            "No additional equipment beyond the baseline above is available at this "
            "household — do not propose dishes needing an oven, microwave, blender, or "
            "any other appliance."
        )

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

    if phase == AgentRunPhase.IDEAS:
        assert mode is not None  # noqa: S101 — guarded above; narrows for mypy
        lines.append(
            "Every final answer must go through the `proposer_idees` tool: propose "
            f"{_idea_count_hint(mode, days)}. Give only a name and a one-line description "
            "for each — never ingredients or steps at this stage, those come later once "
            "the user has picked. If the fridge contents or the request are ambiguous, "
            "call `demander_precision` instead of guessing — never answer with plain text."
        )
        if mode == FridgeInputMode.BATCH and days is not None and days > 1:
            lines.append(
                "This is a batch-cooking session for "
                f"{days} day(s): favor ideas that reuse one cooking effort across several "
                "presentations over the following days, e.g. a big pot of pasta eaten hot "
                "the same evening, as a cold pasta salad the next day, then as a pasta "
                "gratin the day after — mention this kind of reuse explicitly in the "
                "description when it applies."
            )
    else:
        lines.append(
            "Every final answer must go through the `proposer_plats` tool: generate the "
            "full recipe (ingredients and steps) for exactly the dish(es) named in the "
            "preceding tool result, in the same order, and no others. If something is "
            "still ambiguous, call `demander_precision` instead of guessing — never "
            "answer with plain text."
        )
        lines.append(
            "Some fridge items are tagged `[stock#ID]` in the fridge contents below — these "
            "are tracked in the household's persistent inventory. For each dish, set "
            "`ingredients_stock_ids` to the IDs (numbers only, without the `stock#` prefix) "
            "of exactly the tagged items that dish actually uses, so they can be removed "
            "from stock automatically. Leave it empty if none apply, and never invent an ID "
            "that wasn't given to you."
        )
        lines.append(
            "For each dish, also set: `equipment_used` (any appliance beyond the baseline "
            "it actually needs — leave empty if it only needs the baseline), `fridge_days` "
            "(your best estimate of how many days it safely keeps refrigerated after "
            "cooking), and `freezer_friendly` (whether it freezes well). For each "
            "ingredient, set `a_acheter` to true if it's not in the fridge contents or the "
            "pantry staples and the household would need to buy it."
        )

    return "\n".join(lines)


def _idea_count_hint(mode: FridgeInputMode, days: int | None) -> str:
    if mode == FridgeInputMode.BATCH:
        if days is not None:
            return (
                f"enough distinct dish ideas to cover {days} day(s) of batch cooking "
                "(fewer than that is fine when some ideas are meant to be eaten as "
                "leftovers across several of those days)"
            )
        return "6 to 8 distinct dish ideas, enough variety for a week of batch cooking"
    return "3 to 4 distinct dish ideas for a single meal"


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
    name = f"{item.ingredient_name} ({quantity})" if quantity else item.ingredient_name
    if item.fridge_stock_item_id is not None:
        return f"[stock#{item.fridge_stock_item_id}] {name}"
    return name
