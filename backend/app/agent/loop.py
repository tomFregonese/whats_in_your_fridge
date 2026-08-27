"""The agent tool-calling loop.

Two entry points:
- `run()` — synchronous, non-streaming (existing callers).
- `stream_run()` — same logic but streams reasoning tokens via callback.

Calls the model with both tools and interprets the result: either a
clarifying question (stop and wait for the user — see `ClarificationNeeded`)
or a validated, allergy-checked set of proposed dishes (`PlatsProposed`).
Bounded retries handle the model producing malformed tool-call arguments,
no tool call at all, or (see `agent/allergy_check.py`) a dish that
violates a strict household allergy — a real, if uncommon, occurrence
with `:free` models either way.

Dedup context is NOT wired in here yet (see the project plan — a later
milestone adds it as the "recent meals" part of the prompt, without
changing this loop's shape).
"""

import json
from collections.abc import Callable
from dataclasses import dataclass

from openai.types.chat import (
    ChatCompletionMessageFunctionToolCall,
    ChatCompletionMessageParam,
    ChatCompletionMessageToolCallParam,
)
from pydantic import ValidationError

from app.agent import allergy_check, client
from app.agent.output_schema import DemanderPrecisionArgs, ProposerPlatsArgs
from app.agent.tools import DEMANDER_PRECISION, PROPOSER_PLATS, build_tools
from app.domain.allergy import Allergy
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


LoopResult = ClarificationNeeded | PlatsProposed


def run(
    *,
    token: str,
    model: str,
    messages: list[ChatCompletionMessageParam],
    allergies: list[Allergy],
) -> LoopResult:
    tools = build_tools()
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
            # Attempt > 0 here means at least one earlier round (JSON-
            # invalid or allergy-violating) had to be corrected — everyone
            # surviving this round is fairly labeled REGENERATED, not OK.
            status = AllergyCheckStatus.OK if attempt == 0 else AllergyCheckStatus.REGENERATED

            safe_plats, violations = allergy_check.check_all(plats_args.plats, allergies)

            if not violations:
                return PlatsProposed(
                    suggestions=[
                        plat.to_domain(allergy_check_status=status) for plat in safe_plats
                    ],
                    notes_generales=plats_args.notes_generales,
                )

            if attempt == MAX_ATTEMPTS - 1:
                # Out of attempts — resolve now rather than erroring out:
                # keep whatever's safe, drop the rest, and say so.
                dropped_names = [violation.plat.nom for violation in violations]
                note = _dropped_note(plats_args.notes_generales, dropped_names)
                return PlatsProposed(
                    suggestions=[
                        plat.to_domain(allergy_check_status=AllergyCheckStatus.REGENERATED)
                        for plat in safe_plats
                    ],
                    notes_generales=note,
                )

            working_messages.append(
                _tool_error_message(tool_call.id, _violation_message(violations))
            )
            continue

        working_messages.append(_assistant_message(tool_call_param))
        working_messages.append(
            _tool_error_message(
                tool_call.id, f"Unknown tool '{tool_call.function.name}' — use one of the two."
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
    reasoning_callback: Callable[[str], None],
) -> LoopResult:
    """Same tool-calling loop as `run()`, but streams reasoning tokens
    via `reasoning_callback` during each model call.
    """
    tools = build_tools()
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
            status = AllergyCheckStatus.OK if attempt == 0 else AllergyCheckStatus.REGENERATED

            safe_plats, violations = allergy_check.check_all(plats_args.plats, allergies)

            if not violations:
                return PlatsProposed(
                    suggestions=[
                        plat.to_domain(allergy_check_status=status) for plat in safe_plats
                    ],
                    notes_generales=plats_args.notes_generales,
                )

            if attempt == MAX_ATTEMPTS - 1:
                dropped_names = [violation.plat.nom for violation in violations]
                note = _dropped_note(plats_args.notes_generales, dropped_names)
                return PlatsProposed(
                    suggestions=[
                        plat.to_domain(allergy_check_status=AllergyCheckStatus.REGENERATED)
                        for plat in safe_plats
                    ],
                    notes_generales=note,
                )

            working_messages.append(
                _tool_error_message(tool_call.get("id", ""), _violation_message(violations))
            )
            continue

        working_messages.append(_assistant_message(tool_call_param))
        working_messages.append(
            _tool_error_message(
                tool_call.get("id", ""),
                f"Unknown tool '{tool_call.get('function', {}).get('name')}' — use one of the two.",
            )
        )

    raise AgentResponseInvalidError(
        f"The model failed to produce a valid tool call after {MAX_ATTEMPTS} attempts."
    )


def _to_tool_call_param_stream(
    tool_call: dict,
) -> ChatCompletionMessageToolCallParam:
    return {
        "id": tool_call.get("id", ""),
        "type": "function",
        "function": tool_call.get("function", {"name": "", "arguments": ""}),
    }


def _violation_message(violations: list[allergy_check.Violation]) -> str:
    details = "; ".join(f'"{v.plat.nom}" contains {v.allergen}' for v in violations)
    return (
        f"The following dish(es) violate a strict household allergy and cannot be shown: "
        f"{details}. Call `proposer_plats` again with corrected dishes that avoid every "
        "listed allergy entirely."
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
            "You must respond by calling either the `demander_precision` or "
            "`proposer_plats` tool — not with plain text."
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
    """Used by `respond()` to append the user's answer as the tool result
    for a pending `demander_precision` call before resuming the loop.
    """
    return {"role": "tool", "tool_call_id": tool_call_id, "content": content}


def pending_tool_call_id(messages: list[ChatCompletionMessageParam]) -> str:
    """Extracts the tool_call id awaiting a response from a persisted
    conversation — always the last message, an assistant tool call (see
    `ClarificationNeeded.messages`), by construction.
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
