"""The agent tool-calling loop.

Two phases (see `AgentRunPhase`), each with sync + streaming entry points:
- `run_ideas()` / `stream_run_ideas()` — `IDEAS` phase: a shortlist of dish
  ideas (name + description, no ingredients/steps).
- `run()` / `stream_run()` — `RECIPES` phase: the full recipe for exactly
  the idea(s) the user picked (see `selected_dish_names`).

Each entry point calls the model with the phase's two tools and interprets
the result: either a clarifying question (stop and wait for the user — see
`ClarificationNeeded`) or the phase's validated "final answer"
(`IdeasProposed` / `PlatsProposed`). Bounded retries handle the model
producing malformed tool-call arguments, no tool call at all, (`RECIPES`
only, see `agent/allergy_check.py`) a dish that violates a strict
household allergy, or (`RECIPES` only) a recipe that doesn't match what
the user actually selected — all real, if uncommon, occurrences with
`:free` models either way.

The four entry points share the module-level helpers below rather than a
unified abstraction — same sync/streaming duplication already accepted
between the original `run()`/`stream_run()` pair, now also between the
`RECIPES` and `IDEAS` phases.

Dedup context is NOT wired in here yet (see the project plan — a later
milestone adds it as the "recent meals" part of the prompt, without
changing this loop's shape).
"""

import json
from collections.abc import Callable
from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from typing import Any

from openai.types.chat import (
    ChatCompletionMessageFunctionToolCall,
    ChatCompletionMessageParam,
    ChatCompletionMessageToolCallParam,
)
from pydantic import ValidationError

from app.agent import (
    allergy_check,
    client,
    conservation_sanity_check,
    equipment_check,
    sourcing_check,
    stock_reference_check,
)
from app.agent.output_schema import (
    DemanderPrecisionArgs,
    PlatArgs,
    ProposerIdeesArgs,
    ProposerPlatsArgs,
)
from app.agent.tools import DEMANDER_PRECISION, PROPOSER_IDEES, PROPOSER_PLATS, build_tools
from app.domain.agent_run import AgentRunPhase
from app.domain.allergy import Allergy
from app.domain.dish_idea import DishIdea
from app.domain.equipment import Equipment
from app.domain.fridge_input import SourcingMode
from app.domain.suggestion import AllergyCheckStatus, Suggestion
from app.services.exceptions import AgentResponseInvalidError

# "Retries bornés" per the project plan — small on purpose: a `:free` model
# that can't produce a valid, allergy-safe tool call in 3 tries is unlikely
# to on a 4th.
MAX_ATTEMPTS = 3


@dataclass
class ClarificationNeeded:
    question: str
    options: list[str] | None
    messages: list[ChatCompletionMessageParam]
    """Full conversation so far, ending with the assistant's tool call —
    this is exactly what `agent_run.messages_json` persists, and what
    `respond()` (in `services/suggestion_service.py`) resumes from."""


@dataclass
class PlatsProposed:
    suggestions: list[Suggestion]
    notes_generales: str | None


@dataclass
class IdeasProposed:
    ideas: list[DishIdea]
    notes_generales: str | None
    messages: list[ChatCompletionMessageParam]
    """Same role as `ClarificationNeeded.messages` — persisted so `select()`
    (in `services/suggestion_service.py`) can resume the conversation once
    the user has picked."""


LoopResult = ClarificationNeeded | PlatsProposed
IdeasLoopResult = ClarificationNeeded | IdeasProposed


def run(
    *,
    token: str,
    model: str,
    messages: list[ChatCompletionMessageParam],
    allergies: list[Allergy],
    equipment: list[Equipment],
    sourcing_mode: SourcingMode,
    selected_dish_names: list[str],
    known_stock_item_ids: AbstractSet[int] = frozenset(),
) -> LoopResult:
    """`RECIPES` phase: generates the full recipe for exactly
    `selected_dish_names` (the ideas the user picked out of what
    `run_ideas()` proposed). `known_stock_item_ids` are the persistent
    fridge stock item IDs offered to the model in this run's prompt (see
    `agent/prompts.py::_format_item`) — used to sanitize which IDs a dish
    is allowed to claim it used (see `agent/stock_reference_check.py`)."""
    tools = build_tools(AgentRunPhase.RECIPES)
    working_messages = list(messages)

    for attempt in range(MAX_ATTEMPTS):
        message = client.complete_with_tools(
            token=token, model=model, messages=working_messages, tools=tools
        )

        if not message.tool_calls:
            working_messages.append({"role": "assistant", "content": message.content or ""})
            working_messages.append(_retry_nudge_message())
            continue

        tool_call = message.tool_calls[0]
        if not isinstance(tool_call, ChatCompletionMessageFunctionToolCall):
            # We only ever declare function-type tools (see agent/tools.py)
            # — a custom tool call is not something we asked for.
            working_messages.append(_retry_nudge_message())
            continue

        tool_call_param = _to_tool_call_param(tool_call)

        if tool_call.function.name == DEMANDER_PRECISION:
            try:
                precision_args = DemanderPrecisionArgs.model_validate_json(
                    tool_call.function.arguments
                )
            except (ValidationError, ValueError) as exc:
                working_messages.append(_assistant_message(tool_call_param))
                working_messages.append(_tool_error_message(tool_call.id, exc))
                continue
            working_messages.append(_assistant_message(tool_call_param))
            return ClarificationNeeded(
                question=precision_args.question,
                options=precision_args.options,
                messages=working_messages,
            )

        if tool_call.function.name == PROPOSER_PLATS:
            try:
                plats_args = ProposerPlatsArgs.model_validate_json(tool_call.function.arguments)
            except (ValidationError, ValueError) as exc:
                working_messages.append(_assistant_message(tool_call_param))
                working_messages.append(_tool_error_message(tool_call.id, exc))
                continue

            working_messages.append(_assistant_message(tool_call_param))
            last_attempt = attempt == MAX_ATTEMPTS - 1
            # Attempt > 0 here means at least one earlier round (JSON-
            # invalid, allergy-violating, or selection-mismatched) had to
            # be corrected — everyone surviving this round is fairly
            # labeled REGENERATED, not OK.
            status = AllergyCheckStatus.OK if attempt == 0 else AllergyCheckStatus.REGENERATED

            allergy_safe, allergy_violations = allergy_check.check_all(
                plats_args.plats, allergies
            )
            equipment_safe, equipment_violations = equipment_check.check_all(
                allergy_safe, equipment
            )
            safe_plats, sourcing_violations = sourcing_check.check_all(
                equipment_safe, sourcing_mode
            )
            stock_reference_check.sanitize_stock_ids(safe_plats, known_stock_item_ids)
            conservation_sanity_check.sanitize_fridge_days(safe_plats)

            if allergy_violations or equipment_violations or sourcing_violations:
                if last_attempt:
                    # Out of attempts — resolve now rather than erroring
                    # out: keep whatever's safe, drop the rest, and say so.
                    dropped_names = (
                        [v.plat.nom for v in allergy_violations]
                        + [v.plat.nom for v in equipment_violations]
                        + [v.plat.nom for v in sourcing_violations]
                    )
                    note = _dropped_note(plats_args.notes_generales, dropped_names)
                    return PlatsProposed(
                        suggestions=[
                            plat.to_domain(allergy_check_status=AllergyCheckStatus.REGENERATED)
                            for plat in safe_plats
                        ],
                        notes_generales=note,
                    )
                working_messages.append(
                    _tool_error_message(
                        tool_call.id,
                        _combined_violation_message(
                            allergy_violations, equipment_violations, sourcing_violations
                        ),
                    )
                )
                continue

            if not _selection_matches(safe_plats, selected_dish_names) and not last_attempt:
                working_messages.append(
                    _tool_error_message(
                        tool_call.id, _selection_mismatch_message(selected_dish_names)
                    )
                )
                continue

            return PlatsProposed(
                suggestions=[plat.to_domain(allergy_check_status=status) for plat in safe_plats],
                notes_generales=plats_args.notes_generales,
            )

        working_messages.append(_assistant_message(tool_call_param))
        working_messages.append(
            _tool_error_message(
                tool_call.id, f"Unknown tool '{tool_call.function.name}' — use `proposer_plats`."
            )
        )

    raise AgentResponseInvalidError(
        f"The model failed to produce a valid tool call after {MAX_ATTEMPTS} attempts."
    )


def run_ideas(
    *,
    token: str,
    model: str,
    messages: list[ChatCompletionMessageParam],
) -> IdeasLoopResult:
    """`IDEAS` phase: a shortlist of dish ideas for the user to pick from —
    no allergy check here (nothing to check yet, see `agent/allergy_check.py`
    which operates on ingredients), that only happens once `run()` generates
    the full recipe for whatever gets selected."""
    tools = build_tools(AgentRunPhase.IDEAS)
    working_messages = list(messages)

    for _attempt in range(MAX_ATTEMPTS):
        message = client.complete_with_tools(
            token=token, model=model, messages=working_messages, tools=tools
        )

        if not message.tool_calls:
            working_messages.append({"role": "assistant", "content": message.content or ""})
            working_messages.append(_retry_nudge_message())
            continue

        tool_call = message.tool_calls[0]
        if not isinstance(tool_call, ChatCompletionMessageFunctionToolCall):
            working_messages.append(_retry_nudge_message())
            continue

        tool_call_param = _to_tool_call_param(tool_call)

        if tool_call.function.name == DEMANDER_PRECISION:
            try:
                precision_args = DemanderPrecisionArgs.model_validate_json(
                    tool_call.function.arguments
                )
            except (ValidationError, ValueError) as exc:
                working_messages.append(_assistant_message(tool_call_param))
                working_messages.append(_tool_error_message(tool_call.id, exc))
                continue
            working_messages.append(_assistant_message(tool_call_param))
            return ClarificationNeeded(
                question=precision_args.question,
                options=precision_args.options,
                messages=working_messages,
            )

        if tool_call.function.name == PROPOSER_IDEES:
            try:
                idees_args = ProposerIdeesArgs.model_validate_json(tool_call.function.arguments)
            except (ValidationError, ValueError) as exc:
                working_messages.append(_assistant_message(tool_call_param))
                working_messages.append(_tool_error_message(tool_call.id, exc))
                continue

            working_messages.append(_assistant_message(tool_call_param))
            return IdeasProposed(
                ideas=[idee.to_domain() for idee in idees_args.idees],
                notes_generales=idees_args.notes_generales,
                messages=working_messages,
            )

        working_messages.append(_assistant_message(tool_call_param))
        working_messages.append(
            _tool_error_message(
                tool_call.id, f"Unknown tool '{tool_call.function.name}' — use `proposer_idees`."
            )
        )

    raise AgentResponseInvalidError(
        f"The model failed to produce a valid tool call after {MAX_ATTEMPTS} attempts."
    )


def stream_run(
    *,
    token: str,
    model: str,
    messages: list[ChatCompletionMessageParam],
    allergies: list[Allergy],
    equipment: list[Equipment],
    sourcing_mode: SourcingMode,
    selected_dish_names: list[str],
    reasoning_callback: Callable[[str], None],
    known_stock_item_ids: AbstractSet[int] = frozenset(),
) -> LoopResult:
    """Same `RECIPES`-phase loop as `run()`, but streams reasoning tokens
    via `reasoning_callback` during each model call. See `run()`'s
    docstring for `known_stock_item_ids`.
    """
    tools = build_tools(AgentRunPhase.RECIPES)
    working_messages = list(messages)

    for attempt in range(MAX_ATTEMPTS):
        message = client.stream_complete_with_tools(
            token=token,
            model=model,
            messages=working_messages,
            tools=tools,
            reasoning_callback=reasoning_callback,
        )

        if not message.tool_calls:
            working_messages.append({"role": "assistant", "content": message.content or ""})
            working_messages.append(_retry_nudge_message())
            continue

        tool_call = message.tool_calls[0]
        if not isinstance(tool_call, dict) or tool_call.get("type") != "function":
            working_messages.append(_retry_nudge_message())
            continue

        tool_call_param = _to_tool_call_param_stream(tool_call)

        if tool_call.get("function", {}).get("name") == DEMANDER_PRECISION:
            try:
                precision_args = DemanderPrecisionArgs.model_validate_json(
                    tool_call["function"]["arguments"]
                )
            except (ValidationError, ValueError) as exc:
                working_messages.append(_assistant_message(tool_call_param))
                working_messages.append(_tool_error_message(tool_call.get("id", ""), exc))
                continue
            working_messages.append(_assistant_message(tool_call_param))
            return ClarificationNeeded(
                question=precision_args.question,
                options=precision_args.options,
                messages=working_messages,
            )

        if tool_call.get("function", {}).get("name") == PROPOSER_PLATS:
            try:
                plats_args = ProposerPlatsArgs.model_validate_json(
                    tool_call["function"]["arguments"]
                )
            except (ValidationError, ValueError) as exc:
                working_messages.append(_assistant_message(tool_call_param))
                working_messages.append(_tool_error_message(tool_call.get("id", ""), exc))
                continue

            working_messages.append(_assistant_message(tool_call_param))
            last_attempt = attempt == MAX_ATTEMPTS - 1
            status = AllergyCheckStatus.OK if attempt == 0 else AllergyCheckStatus.REGENERATED

            allergy_safe, allergy_violations = allergy_check.check_all(
                plats_args.plats, allergies
            )
            equipment_safe, equipment_violations = equipment_check.check_all(
                allergy_safe, equipment
            )
            safe_plats, sourcing_violations = sourcing_check.check_all(
                equipment_safe, sourcing_mode
            )
            stock_reference_check.sanitize_stock_ids(safe_plats, known_stock_item_ids)
            conservation_sanity_check.sanitize_fridge_days(safe_plats)

            if allergy_violations or equipment_violations or sourcing_violations:
                if last_attempt:
                    dropped_names = (
                        [v.plat.nom for v in allergy_violations]
                        + [v.plat.nom for v in equipment_violations]
                        + [v.plat.nom for v in sourcing_violations]
                    )
                    note = _dropped_note(plats_args.notes_generales, dropped_names)
                    return PlatsProposed(
                        suggestions=[
                            plat.to_domain(allergy_check_status=AllergyCheckStatus.REGENERATED)
                            for plat in safe_plats
                        ],
                        notes_generales=note,
                    )
                working_messages.append(
                    _tool_error_message(
                        tool_call.get("id", ""),
                        _combined_violation_message(
                            allergy_violations, equipment_violations, sourcing_violations
                        ),
                    )
                )
                continue

            if not _selection_matches(safe_plats, selected_dish_names) and not last_attempt:
                working_messages.append(
                    _tool_error_message(
                        tool_call.get("id", ""), _selection_mismatch_message(selected_dish_names)
                    )
                )
                continue

            return PlatsProposed(
                suggestions=[plat.to_domain(allergy_check_status=status) for plat in safe_plats],
                notes_generales=plats_args.notes_generales,
            )

        working_messages.append(_assistant_message(tool_call_param))
        working_messages.append(
            _tool_error_message(
                tool_call.get("id", ""),
                f"Unknown tool '{tool_call.get('function', {}).get('name')}' — "
                "use `proposer_plats`.",
            )
        )

    raise AgentResponseInvalidError(
        f"The model failed to produce a valid tool call after {MAX_ATTEMPTS} attempts."
    )


def stream_run_ideas(
    *,
    token: str,
    model: str,
    messages: list[ChatCompletionMessageParam],
    reasoning_callback: Callable[[str], None],
) -> IdeasLoopResult:
    """Same `IDEAS`-phase loop as `run_ideas()`, but streams reasoning
    tokens via `reasoning_callback` during each model call."""
    tools = build_tools(AgentRunPhase.IDEAS)
    working_messages = list(messages)

    for _attempt in range(MAX_ATTEMPTS):
        message = client.stream_complete_with_tools(
            token=token,
            model=model,
            messages=working_messages,
            tools=tools,
            reasoning_callback=reasoning_callback,
        )

        if not message.tool_calls:
            working_messages.append({"role": "assistant", "content": message.content or ""})
            working_messages.append(_retry_nudge_message())
            continue

        tool_call = message.tool_calls[0]
        if not isinstance(tool_call, dict) or tool_call.get("type") != "function":
            working_messages.append(_retry_nudge_message())
            continue

        tool_call_param = _to_tool_call_param_stream(tool_call)

        if tool_call.get("function", {}).get("name") == DEMANDER_PRECISION:
            try:
                precision_args = DemanderPrecisionArgs.model_validate_json(
                    tool_call["function"]["arguments"]
                )
            except (ValidationError, ValueError) as exc:
                working_messages.append(_assistant_message(tool_call_param))
                working_messages.append(_tool_error_message(tool_call.get("id", ""), exc))
                continue
            working_messages.append(_assistant_message(tool_call_param))
            return ClarificationNeeded(
                question=precision_args.question,
                options=precision_args.options,
                messages=working_messages,
            )

        if tool_call.get("function", {}).get("name") == PROPOSER_IDEES:
            try:
                idees_args = ProposerIdeesArgs.model_validate_json(
                    tool_call["function"]["arguments"]
                )
            except (ValidationError, ValueError) as exc:
                working_messages.append(_assistant_message(tool_call_param))
                working_messages.append(_tool_error_message(tool_call.get("id", ""), exc))
                continue

            working_messages.append(_assistant_message(tool_call_param))
            return IdeasProposed(
                ideas=[idee.to_domain() for idee in idees_args.idees],
                notes_generales=idees_args.notes_generales,
                messages=working_messages,
            )

        working_messages.append(_assistant_message(tool_call_param))
        working_messages.append(
            _tool_error_message(
                tool_call.get("id", ""),
                f"Unknown tool '{tool_call.get('function', {}).get('name')}' — "
                "use `proposer_idees`.",
            )
        )

    raise AgentResponseInvalidError(
        f"The model failed to produce a valid tool call after {MAX_ATTEMPTS} attempts."
    )


def _to_tool_call_param_stream(
    tool_call: dict[str, Any],
) -> ChatCompletionMessageToolCallParam:
    return {
        "id": tool_call.get("id", ""),
        "type": "function",
        "function": tool_call.get("function", {"name": "", "arguments": ""}),
    }


def _combined_violation_message(
    allergy_violations: list[allergy_check.Violation],
    equipment_violations: list[equipment_check.Violation],
    sourcing_violations: list[sourcing_check.Violation],
) -> str:
    parts = []
    if allergy_violations:
        details = "; ".join(f'"{v.plat.nom}" contains {v.allergen}' for v in allergy_violations)
        parts.append(f"violate a strict household allergy ({details})")
    if equipment_violations:
        details = "; ".join(f'"{v.plat.nom}" needs {v.equipment}' for v in equipment_violations)
        parts.append(f"need equipment the household doesn't have ({details})")
    if sourcing_violations:
        details = "; ".join(
            f'"{v.plat.nom}" needs {v.ingredient} bought' for v in sourcing_violations
        )
        parts.append(f"need an ingredient the household asked to avoid buying ({details})")
    return (
        f"The following dish(es) cannot be shown because they {' and/or '.join(parts)}. Call "
        "`proposer_plats` again with corrected dishes that fix every issue listed."
    )


def _selection_matches(plats: list[PlatArgs], selected_dish_names: list[str]) -> bool:
    returned = {plat.nom.strip().casefold() for plat in plats}
    expected = {name.strip().casefold() for name in selected_dish_names}
    return returned == expected


def _selection_mismatch_message(selected_dish_names: list[str]) -> str:
    names = ", ".join(f'"{name}"' for name in selected_dish_names)
    return (
        f"The user selected exactly these dishes: {names}. Call `proposer_plats` again "
        "with the full recipe for exactly these dishes, in this order, and no others."
    )


def _dropped_note(existing_note: str | None, dropped_names: list[str]) -> str | None:
    if not dropped_names:
        return existing_note
    names = ", ".join(f'"{name}"' for name in dropped_names)
    plural = len(dropped_names) > 1
    dropped_message = (
        f"Note: {names} {'were' if plural else 'was'} removed because "
        f"{'they' if plural else 'it'} conflicted with a listed allergy, even after asking "
        "for a correction."
    )
    return f"{existing_note}\n\n{dropped_message}" if existing_note else dropped_message


def _retry_nudge_message() -> ChatCompletionMessageParam:
    return {
        "role": "user",
        "content": (
            "You must respond by calling one of the available tools — not with plain text."
        ),
    }


def _to_tool_call_param(
    tool_call: ChatCompletionMessageFunctionToolCall,
) -> ChatCompletionMessageToolCallParam:
    # Re-declared as a plain dict rather than passed through as-is: the
    # SDK's *response* tool-call type and the *request* tool-call param
    # type are structurally close but distinct (input vs. output types).
    return {
        "id": tool_call.id,
        "type": "function",
        "function": {"name": tool_call.function.name, "arguments": tool_call.function.arguments},
    }


def _assistant_message(
    tool_call_param: ChatCompletionMessageToolCallParam,
) -> ChatCompletionMessageParam:
    # Only the one tool call we're acting on is echoed back, even if the
    # model returned more — keeps the tool-result bookkeeping simple and
    # matches the "one tool call per turn" contract in the system prompt.
    return {"role": "assistant", "content": None, "tool_calls": [tool_call_param]}


def _tool_error_message(tool_call_id: str, error: object) -> ChatCompletionMessageParam:
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "content": f"Invalid arguments: {error}. Please retry with valid arguments.",
    }


def build_tool_result_message(tool_call_id: str, content: str) -> ChatCompletionMessageParam:
    """Used by `respond()` to append the user's clarification answer, and by
    `select()` to append the user's dish selection, as the tool result for
    the pending call before resuming the loop.
    """
    return {"role": "tool", "tool_call_id": tool_call_id, "content": content}


def pending_tool_call_id(messages: list[ChatCompletionMessageParam]) -> str:
    """Extracts the tool_call id awaiting a response from a persisted
    conversation — always the last message, an assistant tool call (see
    `ClarificationNeeded.messages` / `IdeasProposed.messages`), by
    construction.
    """
    last = messages[-1]
    tool_calls = last.get("tool_calls") if isinstance(last, dict) else None
    if not isinstance(tool_calls, list) or not tool_calls:
        raise AgentResponseInvalidError(
            "Stored conversation doesn't end with a pending tool call."
        )

    first = tool_calls[0]
    call_id = first.get("id") if isinstance(first, dict) else None
    if not isinstance(call_id, str):
        raise AgentResponseInvalidError("Stored tool call is missing its id.")
    return call_id


def serialize_messages(messages: list[ChatCompletionMessageParam]) -> str:
    return json.dumps(messages)


def deserialize_messages(raw: str) -> list[ChatCompletionMessageParam]:
    result: list[ChatCompletionMessageParam] = json.loads(raw)
    return result
