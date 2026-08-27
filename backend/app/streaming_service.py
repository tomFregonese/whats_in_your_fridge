"""Background streaming infrastructure — bridges the synchronous agent loop
with async SSE delivery.

Designed for exactly-once, per-run use: create a run via
`StreamingOrchestrator.start_stream()`, subscribe via
`StreamingOrchestrator.sse_generator()`, then clean up automatically when
the stream or the background thread finishes.
"""

from __future__ import annotations

import asyncio
import json
import queue
import threading
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

from app.agent import loop
from app.agent.dedup import DedupProvider
from app.agent.loop import LoopResult
from app.domain.agent_run import AgentRun, AgentRunStatus
from app.domain.fridge_input import FridgeInput
from app.domain.suggestion import MealPlan
from app.persistence.repositories.agent_run_repository import AgentRunRepository
from app.persistence.repositories.allergy_repository import AllergyRepository
from app.persistence.repositories.fridge_input_repository import FridgeInputRepository
from app.persistence.repositories.suggestion_repository import SuggestionRepository
from app.security.service import SecurityService
from app.services.exceptions import NotFoundError
from app.services.settings_service import SettingsService

# Per-run in-memory state — keyed by agent_run DB id.
_buffers: dict[int, queue.Queue] = {}
_done_events: dict[int, threading.Event] = {}
_answer_ready: dict[int, threading.Event] = {}
_answers: dict[int, str] = {}
_locks: dict[int, threading.Lock] = {}
_background_threads: dict[int, threading.Thread] = {}


def _event(run_id: int, **kwargs: object) -> None:
    """Push a JSON-serialisable event into the run's buffer."""
    buf = _buffers.get(run_id)
    if buf is not None:
        buf.put_nowait(kwargs)


def _cleanup(run_id: int) -> None:
    _buffers.pop(run_id, None)
    _done_events.pop(run_id, None)
    _answer_ready.pop(run_id, None)
    _answers.pop(run_id, None)
    _locks.pop(run_id, None)
    _background_threads.pop(run_id, None)


def _run_loop(
    run_id: int,
    token: str,
    messages: list[dict],
    model: str,
    allergies: list,
) -> LoopResult:
    """Same logic as `SuggestionService._run_loop` but with streaming."""
    result = loop.stream_run(
        token=token,
        model=model,
        messages=messages,
        allergies=allergies,
        reasoning_callback=lambda text: _event(run_id, type="reasoning", content=text),
    )
    return result


def start_background(
    *,
    run_id: int,
    fridge_input: FridgeInput,
    messages: list[dict],
    existing_run_id: int | None,
    token: str,
    model: str,
    allergies: list,
    fridge_input_repository: FridgeInputRepository,
    agent_run_repository: AgentRunRepository,
    suggestion_repository: SuggestionRepository,
    settings_service: SettingsService,
    security_service: SecurityService,
    dedup_provider: DedupProvider,
) -> None:
    """Start a background thread that runs the agent loop with streaming.

    Must be called AFTER ``_init(run_id)`` so the buffer exists.
    The thread writes ``reasoning``, ``completed``, ``clarification``,
    ``error``, and ``done`` events into the per-run buffer.
    """
    buf = queue.Queue()
    done = threading.Event()
    answer_ready = threading.Event()

    _buffers[run_id] = buf
    _done_events[run_id] = done
    _answer_ready[run_id] = answer_ready
    _answers[run_id] = ""
    _locks[run_id] = threading.Lock()

    def _background() -> None:
        try:
            loop_result = _run_loop(
                run_id=run_id,
                token=token,
                messages=messages,
                model=model,
                allergies=allergies,
            )

            if isinstance(loop_result, loop.ClarificationNeeded):
                # Persist the agent run and send clarification event
                saved_run = agent_run_repository.save(
                    AgentRun(
                        id=existing_run_id,
                        fridge_input_id=fridge_input.id,
                        status=AgentRunStatus.AWAITING_CLARIFICATION,
                        messages_json=loop.serialize_messages(loop_result.messages),
                        pending_question=loop_result.question,
                    )
                )
                _event(
                    run_id,
                    type="clarification",
                    run_id=saved_run.id,
                    question=loop_result.question,
                    options=loop_result.options,
                )

                # Wait for the user to respond
                answer_ready.wait()
                user_answer = _answers[run_id]

                # Resume loop with the user's answer
                tool_call_id = loop.pending_tool_call_id(loop_result.messages)
                loop_result.messages.append(loop.build_tool_result_message(tool_call_id, user_answer))

                # Re-run the loop with the clarification answer (one more call)
                loop_result = _run_loop(
                    run_id=run_id,
                    token=token,
                    messages=loop_result.messages,
                    model=model,
                    allergies=allergies,
                )

            # Now handle the final result
            if isinstance(loop_result, loop.PlatsProposed):
                saved_meal_plan = suggestion_repository.add(
                    MealPlan(
                        id=None,
                        fridge_input_id=fridge_input.id,
                        mode=fridge_input.mode,
                        created_at=datetime.now(UTC),
                        suggestions=loop_result.suggestions,
                    )
                )
                _event(
                    run_id,
                    type="completed",
                    meal_plan_id=saved_meal_plan.id,
                    notes_generales=loop_result.notes_generales,
                )

        except Exception as exc:
            _event(run_id, type="error", detail=str(exc))
        finally:
            _event(run_id, type="done")
            done.set()
            _buffers.pop(run_id, None)

    thread = threading.Thread(target=_background, daemon=True)
    _background_threads[run_id] = thread
    thread.start()


def deliver_answer(run_id: int, answer: str) -> None:
    """Called from the ``respond-stream`` controller endpoint to unblock
    the background thread waiting on a clarification answer.
    """
    ready = _answer_ready.get(run_id)
    if ready is None:
        raise NotFoundError(f"No active streaming session for run {run_id}.")
    _answers[run_id] = answer
    ready.set()
    # Cleanup per-run answer controls so they don't leak
    _answer_ready.pop(run_id, None)


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