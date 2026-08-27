"""Exercises the actual background thread in `streaming_service.py` end to
end — the restructured two-phase (`IDEAS` -> `RECIPES`) event loop that
`test_suggestions.py` only reaches indirectly through the sync endpoints.
Uses real repositories against the test `session` fixture (persistence
must actually happen from the background thread), but mocks the agent
loop functions the same way `test_suggestions.py` does.
"""

import queue
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from sqlmodel import Session

from app import streaming_service as ss
from app.agent import loop
from app.domain.agent_run import AgentRunStatus
from app.domain.dish_idea import DishIdea
from app.domain.fridge_input import FridgeInput, FridgeInputMode
from app.domain.suggestion import AllergyCheckStatus, Suggestion
from app.persistence.repositories.agent_run_repository import AgentRunRepository
from app.persistence.repositories.fridge_input_repository import FridgeInputRepository
from app.persistence.repositories.suggestion_repository import SuggestionRepository


def _drain_until(
    run_id: int, target_type: str, *, timeout: float = 2.0
) -> list[dict[str, object]]:
    """Reads events off the run's buffer until (and including) one of type
    `target_type`, failing the test if it never shows up in time."""
    buf = ss._buffers[run_id]
    collected: list[dict[str, object]] = []
    while True:
        try:
            event = buf.get(timeout=timeout)
        except queue.Empty:
            raise AssertionError(
                f"Timed out waiting for a '{target_type}' event; got so far: {collected}"
            ) from None
        collected.append(event)
        if event.get("type") == target_type:
            return collected


def _start(session: Session, *, mode: FridgeInputMode = FridgeInputMode.BATCH) -> int:
    fridge_input_repository = FridgeInputRepository(session)
    saved_input = fridge_input_repository.add(
        FridgeInput(id=None, mode=mode, free_text="carrot", created_at=datetime.now(UTC))
    )
    assert saved_input.id is not None
    run_id = saved_input.id

    ss.start_background(
        run_id=run_id,
        fridge_input=saved_input,
        messages=[{"role": "system", "content": "sys"}, {"role": "user", "content": "hi"}],
        token="tok",
        model="m",
        allergies=[],
        fridge_input_repository=fridge_input_repository,
        agent_run_repository=AgentRunRepository(session),
        suggestion_repository=SuggestionRepository(session),
        settings_service=MagicMock(),
        security_service=MagicMock(),
        dedup_provider=MagicMock(),
    )
    return run_id


def _ideas_proposed() -> loop.IdeasProposed:
    return loop.IdeasProposed(
        ideas=[DishIdea(dish_name="Carrot soup", description="Simple soup")],
        notes_generales=None,
        messages=[
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hi"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "proposer_idees", "arguments": "{}"},
                    }
                ],
            },
        ],
    )


def _plats_proposed() -> loop.PlatsProposed:
    return loop.PlatsProposed(
        suggestions=[
            Suggestion(
                id=None,
                meal_plan_id=None,
                dish_name="Carrot soup",
                description="Simple soup",
                ingredients_json='["carrot (3)"]',
                steps_json='["Boil.", "Blend."]',
                servings=4,
                allergy_check_status=AllergyCheckStatus.OK,
            )
        ],
        notes_generales="Enjoy!",
    )


def test_full_two_phase_stream_persists_meal_plan(session: Session) -> None:
    with patch("app.streaming_service.loop.stream_run_ideas", return_value=_ideas_proposed()):
        run_id = _start(session)
        ideas_events = _drain_until(run_id, "ideas")

    ideas_event = ideas_events[-1]
    assert ideas_event["ideas"] == [
        {"index": 0, "dish_name": "Carrot soup", "description": "Simple soup"}
    ]
    # The DB agent_run id travels in the payload too (for parity with the
    # non-streaming Dto), distinct from `run_id` (the fridge_input id).
    agent_run_id = ideas_event["run_id"]
    assert isinstance(agent_run_id, int)

    agent_run = AgentRunRepository(session).get(agent_run_id)
    assert agent_run is not None
    assert agent_run.status == AgentRunStatus.AWAITING_SELECTION
    assert agent_run.proposed_ideas_json is not None

    with patch("app.streaming_service.loop.stream_run", return_value=_plats_proposed()) as mock_run:
        ss.deliver_selection(run_id, [0])
        completed_events = _drain_until(run_id, "completed")

    completed_event = completed_events[-1]
    meal_plan_id = completed_event["meal_plan_id"]
    assert isinstance(meal_plan_id, int)
    assert completed_event["notes_generales"] == "Enjoy!"
    assert mock_run.call_args.kwargs["selected_dish_names"] == ["Carrot soup"]

    meal_plan = SuggestionRepository(session).get(meal_plan_id)
    assert meal_plan is not None
    assert meal_plan.suggestions[0].dish_name == "Carrot soup"

    agent_run = AgentRunRepository(session).get(agent_run_id)
    assert agent_run is not None
    assert agent_run.status == AgentRunStatus.COMPLETED


def test_clarification_during_ideas_phase_then_ideas_proposed(session: Session) -> None:
    clarification = loop.ClarificationNeeded(
        question="How many people?",
        options=None,
        messages=[
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hi"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "demander_precision", "arguments": "{}"},
                    }
                ],
            },
        ],
    )

    with patch("app.streaming_service.loop.stream_run_ideas", return_value=clarification):
        run_id = _start(session)
        clarification_events = _drain_until(run_id, "clarification")

    assert clarification_events[-1]["question"] == "How many people?"
    agent_run_id = clarification_events[-1]["run_id"]
    assert isinstance(agent_run_id, int)
    agent_run = AgentRunRepository(session).get(agent_run_id)
    assert agent_run is not None
    assert agent_run.status == AgentRunStatus.AWAITING_CLARIFICATION

    with patch(
        "app.streaming_service.loop.stream_run_ideas", return_value=_ideas_proposed()
    ) as mock_ideas:
        ss.deliver_answer(run_id, "4 people")
        ideas_events = _drain_until(run_id, "ideas")

    ideas_payload = ideas_events[-1]["ideas"]
    assert isinstance(ideas_payload, list)
    assert ideas_payload[0]["dish_name"] == "Carrot soup"
    sent_messages = mock_ideas.call_args.kwargs["messages"]
    assert sent_messages[-1] == {"role": "tool", "tool_call_id": "call_1", "content": "4 people"}
