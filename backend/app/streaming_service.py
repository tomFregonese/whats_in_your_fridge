"""Background streaming infrastructure — bridges the synchronous agent loop
with async SSE delivery.

Designed for exactly-once, per-run use: create a run via
``start_background()``, subscribe via ``sse_generator()``, then clean up
automatically when the stream or the background thread finishes.

The background thread walks both agent phases (`AgentRunPhase`) in one
loop — `IDEAS` then `RECIPES` — pausing for either a clarification answer
or (once, between phases) a dish selection, each delivered from the
``respond-stream``/``select-stream`` controller endpoints via
``deliver_answer()``/``deliver_selection()``. Either phase may pause for
0 or more clarification rounds before producing its "final answer", same
as the non-streaming loop in `agent/loop.py`.

Every per-run dict below is keyed by the *streaming* run id (the
`fridge_input.id` passed into ``start_background()``), not the DB
`agent_run.id` — the frontend only ever addresses a stream by the former
(see `FridgeInputForm.tsx`); the latter travels in SSE event payloads only
for parity with the non-streaming Dto shape.
"""

from __future__ import annotations

import asyncio
import json
import queue
import threading
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

from openai.types.chat import ChatCompletionMessageParam

from app.agent import loop
from app.agent.dedup import DedupProvider
from app.agent.loop import IdeasLoopResult, LoopResult
from app.domain.agent_run import AgentRun, AgentRunPhase, AgentRunStatus
from app.domain.allergy import Allergy
from app.domain.dish_idea import DishIdea
from app.domain.equipment import Equipment
from app.domain.fridge_input import FridgeInput, FridgeInputMode
from app.domain.fridge_stock import FridgeStockItem
from app.domain.suggestion import AgendaEntry, MealPlan
from app.persistence.repositories.agent_run_repository import AgentRunRepository
from app.persistence.repositories.fridge_input_repository import FridgeInputRepository
from app.persistence.repositories.suggestion_repository import SuggestionRepository
from app.security.service import SecurityService
from app.services.exceptions import NotFoundError
from app.services.fridge_stock_service import FridgeStockService
from app.services.meal_agenda_service import DishForAgenda, build_agenda
from app.services.settings_service import SettingsService

# Per-run in-memory state — keyed by the streaming run id.
_buffers: dict[int, queue.Queue[dict[str, object]]] = {}
_done_events: dict[int, threading.Event] = {}
_input_ready: dict[int, threading.Event] = {}
_answers: dict[int, str] = {}
_selections: dict[int, list[int]] = {}
_background_threads: dict[int, threading.Thread] = {}


def _event(run_id: int, payload: dict[str, object]) -> None:
    """Push a JSON-serialisable event into the run's buffer. `payload` is a
    plain dict (rather than `**kwargs`) so it can freely carry its own
    `run_id` key (the DB `agent_run.id`, for parity with the non-streaming
    Dto shape) without colliding with this function's own `run_id`
    parameter (the streaming run id used to look up the buffer).
    """
    buf = _buffers.get(run_id)
    if buf is not None:
        buf.put_nowait(payload)


def _cleanup(run_id: int) -> None:
    _buffers.pop(run_id, None)
    _done_events.pop(run_id, None)
    _input_ready.pop(run_id, None)
    _answers.pop(run_id, None)
    _selections.pop(run_id, None)
    _background_threads.pop(run_id, None)


def _encode_ideas_json(ideas: list[DishIdea]) -> str:
    return json.dumps([{"dish_name": i.dish_name, "description": i.description} for i in ideas])


def _stock_item_to_dict(item: FridgeStockItem) -> dict[str, object]:
    """Shapes a removed `FridgeStockItem` for the `"completed"` SSE event —
    kept a plain dict (like every other event payload here) rather than a
    Dto import, matching this module's existing style; mirrors
    `FridgeStockItemDtoOut`'s fields on the non-streaming response."""
    return {
        "id": item.id,
        "ingredient_name": item.ingredient_name,
        "quantity_value": item.quantity_value,
        "quantity_unit": item.quantity_unit,
        "quantity_raw": item.quantity_raw,
    }


def _agenda_entry_to_dict(entry: AgendaEntry) -> dict[str, object]:
    """Shapes an `AgendaEntry` for the `"completed"` SSE event — same
    plain-dict convention as `_stock_item_to_dict`; mirrors
    `AgendaEntryDtoOut`'s fields on the non-streaming response."""
    return {
        "id": entry.id,
        "day_index": entry.day_index,
        "suggestion_id": entry.suggestion_id,
        "storage": entry.storage.value,
        "warning": entry.warning,
    }


def _stream_run_ideas(
    *, run_id: int, token: str, model: str, messages: list[ChatCompletionMessageParam]
) -> IdeasLoopResult:
    return loop.stream_run_ideas(
        token=token,
        model=model,
        messages=messages,
        reasoning_callback=lambda text: _event(run_id, {"type": "reasoning", "content": text}),
    )


def _stream_run_recipes(
    *,
    run_id: int,
    token: str,
    model: str,
    messages: list[ChatCompletionMessageParam],
    allergies: list[Allergy],
    equipment: list[Equipment],
    selected_dish_names: list[str],
    known_stock_item_ids: set[int],
) -> LoopResult:
    return loop.stream_run(
        token=token,
        model=model,
        messages=messages,
        allergies=allergies,
        equipment=equipment,
        selected_dish_names=selected_dish_names,
        known_stock_item_ids=known_stock_item_ids,
        reasoning_callback=lambda text: _event(run_id, {"type": "reasoning", "content": text}),
    )


def start_background(
    *,
    run_id: int,
    fridge_input: FridgeInput,
    messages: list[ChatCompletionMessageParam],
    token: str,
    model: str,
    allergies: list[Allergy],
    equipment: list[Equipment],
    fridge_input_repository: FridgeInputRepository,
    agent_run_repository: AgentRunRepository,
    suggestion_repository: SuggestionRepository,
    settings_service: SettingsService,
    security_service: SecurityService,
    dedup_provider: DedupProvider,
    fridge_stock_service: FridgeStockService,
) -> None:
    """Start a background thread running the two-phase agent loop with
    streaming. `messages` is the `IDEAS`-phase system+user prompt.

    Must be called AFTER the buffer exists (it creates it). The thread
    writes ``reasoning``, ``ideas``, ``clarification``, ``completed``,
    ``error``, and ``done`` events into the per-run buffer.
    """
    buf: queue.Queue[dict[str, object]] = queue.Queue()
    done = threading.Event()
    input_ready = threading.Event()

    _buffers[run_id] = buf
    _done_events[run_id] = done
    _input_ready[run_id] = input_ready

    def _background() -> None:
        assert fridge_input.id is not None
        phase = AgentRunPhase.IDEAS
        current_messages = messages
        run_db_id: int | None = None
        selected_dish_names: list[str] = []
        ideas_so_far: list[DishIdea] = []
        known_stock_item_ids = {
            item.fridge_stock_item_id
            for item in fridge_input.items
            if item.fridge_stock_item_id is not None
        }

        try:
            while True:
                if phase == AgentRunPhase.IDEAS:
                    ideas_result = _stream_run_ideas(
                        run_id=run_id, token=token, model=model, messages=current_messages
                    )
                    phase_result: IdeasLoopResult | LoopResult = ideas_result
                else:
                    phase_result = _stream_run_recipes(
                        run_id=run_id,
                        token=token,
                        model=model,
                        messages=current_messages,
                        allergies=allergies,
                        equipment=equipment,
                        selected_dish_names=selected_dish_names,
                        known_stock_item_ids=known_stock_item_ids,
                    )

                if isinstance(phase_result, loop.ClarificationNeeded):
                    saved_run = agent_run_repository.save(
                        AgentRun(
                            id=run_db_id,
                            fridge_input_id=fridge_input.id,
                            status=AgentRunStatus.AWAITING_CLARIFICATION,
                            phase=phase,
                            messages_json=loop.serialize_messages(phase_result.messages),
                            pending_question=phase_result.question,
                            proposed_ideas_json=(
                                _encode_ideas_json(
                                    [
                                        DishIdea(dish_name=n, description="")
                                        for n in selected_dish_names
                                    ]
                                )
                                if phase == AgentRunPhase.RECIPES
                                else None
                            ),
                        )
                    )
                    run_db_id = saved_run.id
                    _event(
                        run_id,
                        {
                            "type": "clarification",
                            "run_id": saved_run.id,
                            "question": phase_result.question,
                            "options": phase_result.options,
                        },
                    )

                    input_ready.wait()
                    input_ready.clear()
                    answer = _answers.pop(run_id, "")

                    tool_call_id = loop.pending_tool_call_id(phase_result.messages)
                    current_messages = list(phase_result.messages)
                    current_messages.append(loop.build_tool_result_message(tool_call_id, answer))
                    continue  # same phase, one more round

                if isinstance(phase_result, loop.IdeasProposed):
                    ideas_so_far = phase_result.ideas
                    saved_run = agent_run_repository.save(
                        AgentRun(
                            id=run_db_id,
                            fridge_input_id=fridge_input.id,
                            status=AgentRunStatus.AWAITING_SELECTION,
                            phase=AgentRunPhase.IDEAS,
                            messages_json=loop.serialize_messages(phase_result.messages),
                            pending_question=None,
                            proposed_ideas_json=_encode_ideas_json(ideas_so_far),
                        )
                    )
                    run_db_id = saved_run.id
                    _event(
                        run_id,
                        {
                            "type": "ideas",
                            "run_id": saved_run.id,
                            "ideas": [
                                {
                                    "index": i,
                                    "dish_name": idea.dish_name,
                                    "description": idea.description,
                                }
                                for i, idea in enumerate(ideas_so_far)
                            ],
                            "notes_generales": phase_result.notes_generales,
                        },
                    )

                    input_ready.wait()
                    input_ready.clear()
                    selected_indexes = _selections.pop(run_id, [])
                    selected = [ideas_so_far[i] for i in selected_indexes]
                    selected_dish_names = [idea.dish_name for idea in selected]

                    tool_call_id = loop.pending_tool_call_id(phase_result.messages)
                    names = ", ".join(f'"{n}"' for n in selected_dish_names)
                    content = (
                        f"The user selected: {names}. Call `proposer_plats` now with the "
                        "full recipe for exactly these dishes, in this order, and no others."
                    )
                    current_messages = list(phase_result.messages)
                    current_messages.append(loop.build_tool_result_message(tool_call_id, content))
                    phase = AgentRunPhase.RECIPES
                    continue

                # Only PlatsProposed remains — the RECIPES phase's final answer.
                assert run_db_id is not None
                existing = agent_run_repository.get(run_db_id)
                assert existing is not None
                agent_run_repository.save(
                    AgentRun(
                        id=run_db_id,
                        fridge_input_id=fridge_input.id,
                        status=AgentRunStatus.COMPLETED,
                        phase=AgentRunPhase.RECIPES,
                        messages_json=existing.messages_json,
                        pending_question=None,
                        proposed_ideas_json=None,
                    )
                )
                saved_meal_plan = suggestion_repository.add(
                    MealPlan(
                        id=None,
                        fridge_input_id=fridge_input.id,
                        mode=fridge_input.mode,
                        created_at=datetime.now(UTC),
                        suggestions=phase_result.suggestions,
                    )
                )

                used_stock_ids = sorted(
                    {
                        stock_id
                        for suggestion in saved_meal_plan.suggestions
                        for stock_id in json.loads(suggestion.used_stock_item_ids_json)
                    }
                )
                removed_items = (
                    fridge_stock_service.deduct(used_stock_ids) if used_stock_ids else []
                )

                agenda: list[AgendaEntry] = []
                assert saved_meal_plan.id is not None
                if fridge_input.mode == FridgeInputMode.BATCH and fridge_input.days is not None:
                    freezer_capacity_slots = settings_service.get_settings().freezer_capacity_slots
                    built = build_agenda(
                        dishes=[
                            DishForAgenda(
                                suggestion_id=s.id,
                                fridge_days=s.fridge_days,
                                freezer_friendly=s.freezer_friendly,
                            )
                            for s in saved_meal_plan.suggestions
                            if s.id is not None
                        ],
                        days=fridge_input.days,
                        freezer_capacity_slots=freezer_capacity_slots,
                    )
                    agenda = suggestion_repository.add_agenda(saved_meal_plan.id, built)

                _event(
                    run_id,
                    {
                        "type": "completed",
                        "meal_plan_id": saved_meal_plan.id,
                        "notes_generales": phase_result.notes_generales,
                        "agenda": [_agenda_entry_to_dict(entry) for entry in agenda],
                        "removed_stock_items": [
                            _stock_item_to_dict(item) for item in removed_items
                        ],
                    },
                )
                break

        except Exception as exc:
            _event(run_id, {"type": "error", "detail": str(exc)})
        finally:
            _event(run_id, {"type": "done"})
            done.set()
            _buffers.pop(run_id, None)

    thread = threading.Thread(target=_background, daemon=True)
    _background_threads[run_id] = thread
    thread.start()


def deliver_answer(run_id: int, answer: str) -> None:
    """Called from the ``respond-stream`` controller endpoint to unblock
    the background thread waiting on a clarification answer, in either
    phase.
    """
    ready = _input_ready.get(run_id)
    if ready is None:
        raise NotFoundError(f"No active streaming session for run {run_id}.")
    _answers[run_id] = answer
    ready.set()


def deliver_selection(run_id: int, selected_indexes: list[int]) -> None:
    """Called from the ``select-stream`` controller endpoint to unblock the
    background thread waiting on a dish selection after the `IDEAS` phase.
    """
    ready = _input_ready.get(run_id)
    if ready is None:
        raise NotFoundError(f"No active streaming session for run {run_id}.")
    _selections[run_id] = selected_indexes
    ready.set()


async def sse_generator(run_id: int) -> AsyncGenerator[str, None]:
    """Async generator for ``StreamingResponse`` — yields SSE events from
    the background thread's buffer.

    Each event is a JSON-serialised dict prefixed with ``data: `` as
    required by the SSE specification.
    """
    buf = _buffers.get(run_id)
    done = _done_events.get(run_id)
    if buf is None or done is None:
        yield f"data: {json.dumps({'type': 'error', 'detail': 'Stream not found.'})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
        return

    while True:
        # Drain all available events
        while not buf.empty():
            try:
                event = buf.get_nowait()
            except queue.Empty:
                break
            yield f"data: {json.dumps(event)}\n\n"
            if event.get("type") == "done":
                return

        if done.is_set():
            # One final drain
            while not buf.empty():
                try:
                    event = buf.get_nowait()
                except queue.Empty:
                    break
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("type") == "done":
                    return
            break

        await asyncio.sleep(0.05)

    _cleanup(run_id)
