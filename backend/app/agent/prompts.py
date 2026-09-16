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
from app.domain.dish_idea import DishIdea
from app.domain.equipment import Equipment
from app.domain.fridge_input import (
    FridgeInput,
    FridgeInputItem,
    FridgeInputMode,
    SourcingMode,
)
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
    sourcing_mode: SourcingMode,
    mode: FridgeInputMode | None = None,
    days: int | None = None,
    dedup_context: str = "",
) -> str:
    if phase == AgentRunPhase.IDEAS and mode is None:
        raise ValueError("`mode` is required to size the idea shortlist in the IDEAS phase.")

    lines = [
        "You are a batch-cooking assistant for a self-hosted household app.",
        _sourcing_instruction(sourcing_mode),
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
                f"{days} day(s). NEVER plan to eat the exact same dish, unchanged, on more "
                "than one day — eating identical leftovers day after day is not acceptable. "
                "When one cooking effort is meant to cover several days, propose a separate "
                "idea for each day's presentation, each genuinely different (a big pot of "
                "pasta eaten hot the same evening, a cold pasta salad the next day, a pasta "
                "gratin the day after — never the same pasta served the same way twice). "
                "For each such follow-up idea, set `restes_de` to the exact `nom` of the "
                "earlier idea in this same list whose leftovers it reuses, and "
                "`transformation` to a short description of what changes about it. Chaining "
                "reuse across more than two days (e.g. pasta → pasta salad → pasta gratin) "
                "is encouraged when it fits."
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
        lines.append(
            "If the preceding tool result says a dish reuses another selected dish's "
            "leftovers, restate that on `proposer_plats`: set `restes_de` to the exact "
            "`nom` of that other dish as it appears in this same call, and `transformation` "
            "to how the leftovers are turned into this dish — never invent a leftover link "
            "that wasn't given to you, and never point `restes_de` at a dish outside this "
            "same selection."
        )

    return "\n".join(lines)


def _sourcing_instruction(sourcing_mode: SourcingMode) -> str:
    if sourcing_mode == SourcingMode.FRIDGE_ONLY:
        return (
            "Only propose dishes fully makeable from the fridge contents below plus the "
            "pantry staples — never include an ingredient that would need to be bought, "
            "and never set `a_acheter` to true on any ingredient."
        )
    if sourcing_mode == SourcingMode.SHOPPING_ONLY:
        return (
            "The household is planning a shopping trip, not trying to use up the fridge — "
            "don't limit dish ideas to the fridge contents below. Set `a_acheter` to true "
            "on every ingredient that isn't a pantry staple or already in the fridge "
            "contents, so it ends up on the shopping list."
        )
    return (
        "Suggest dishes to cook primarily from what's in the fridge — a few ingredients "
        "the household doesn't have are fine as long as they're clearly flagged (see "
        "`a_acheter` below) so they end up on a shopping list, rather than silently "
        "assumed available."
    )


def _idea_count_hint(mode: FridgeInputMode, days: int | None) -> str:
    if mode == FridgeInputMode.BATCH:
        if days is not None:
            return (
                f"enough distinct dish ideas or leftover presentations to cover all "
                f"{days} day(s) of batch cooking — never fewer than {days}, since each day "
                "needs either a new dish or a genuinely different presentation of a "
                "previous day's leftovers (see `restes_de` below), never the same dish "
                "repeated as-is"
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


def build_selection_message(selected: list[DishIdea]) -> str:
    """Tool-result content resuming a pending `proposer_idees` call once the
    user has picked, forcing the model straight into `proposer_plats` for
    exactly those dishes — shared by `SuggestionService.select()` and
    `streaming_service.py`'s background thread (previously built ad hoc,
    near-identically, in both places).

    Also reminds the model of any leftover chain among the picks (see
    `DishIdea.leftover_of_dish_name`) — once `select()` resumes the
    conversation, the picked ideas are the only place that link still
    lives, so it has to be restated here for the model to carry it over
    onto `PlatArgs.restes_de`/`transformation`.
    """
    names = ", ".join(f'"{idea.dish_name}"' for idea in selected)
    lines = [
        f"The user selected: {names}. Call `proposer_plats` now with the full recipe for "
        "exactly these dishes, in this order, and no others."
    ]
    for idea in selected:
        if idea.leftover_of_dish_name:
            note = f" ({idea.transformation_note})" if idea.transformation_note else ""
            lines.append(
                f'"{idea.dish_name}" reuses the leftovers of "{idea.leftover_of_dish_name}"'
                f"{note} — set `restes_de`/`transformation` on `proposer_plats` accordingly."
            )
    return " ".join(lines)


def _format_item(item: FridgeInputItem) -> str:
    quantity = item.quantity_raw
    if quantity is None and item.quantity_value is not None:
        quantity = f"{item.quantity_value} {item.quantity_unit or ''}".strip()
    name = f"{item.ingredient_name} ({quantity})" if quantity else item.ingredient_name
    if item.fridge_stock_item_id is not None:
        return f"[stock#{item.fridge_stock_item_id}] {name}"
    return name
