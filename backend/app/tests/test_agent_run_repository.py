from datetime import UTC, datetime

from sqlmodel import Session

from app.domain.agent_run import AgentRun, AgentRunPhase, AgentRunStatus
from app.domain.fridge_input import FridgeInput, FridgeInputMode
from app.persistence.repositories.agent_run_repository import AgentRunRepository
from app.persistence.repositories.fridge_input_repository import FridgeInputRepository


def _fridge_input_id(session: Session) -> int:
    repo = FridgeInputRepository(session)
    saved = repo.add(
        FridgeInput(
            id=None, mode=FridgeInputMode.BATCH, free_text="x", created_at=datetime.now(UTC)
        )
    )
    assert saved.id is not None
    return saved.id


def test_get_returns_none_when_missing(session: Session) -> None:
    repo = AgentRunRepository(session)

    assert repo.get(999) is None


def test_save_creates_new_row(session: Session) -> None:
    repo = AgentRunRepository(session)
    fridge_input_id = _fridge_input_id(session)

    saved = repo.save(
        AgentRun(
            id=None,
            fridge_input_id=fridge_input_id,
            status=AgentRunStatus.AWAITING_CLARIFICATION,
            phase=AgentRunPhase.IDEAS,
            messages_json="[]",
            pending_question="How many people?",
            proposed_ideas_json=None,
        )
    )

    assert saved.id is not None
    fetched = repo.get(saved.id)
    assert fetched is not None
    assert fetched.status == AgentRunStatus.AWAITING_CLARIFICATION
    assert fetched.phase == AgentRunPhase.IDEAS
    assert fetched.pending_question == "How many people?"


def test_save_updates_existing_row(session: Session) -> None:
    repo = AgentRunRepository(session)
    fridge_input_id = _fridge_input_id(session)
    created = repo.save(
        AgentRun(
            id=None,
            fridge_input_id=fridge_input_id,
            status=AgentRunStatus.AWAITING_CLARIFICATION,
            phase=AgentRunPhase.IDEAS,
            messages_json="[]",
            pending_question="How many people?",
            proposed_ideas_json=None,
        )
    )
    assert created.id is not None

    updated = repo.save(
        AgentRun(
            id=created.id,
            fridge_input_id=fridge_input_id,
            status=AgentRunStatus.COMPLETED,
            phase=AgentRunPhase.RECIPES,
            messages_json='["done"]',
            pending_question=None,
            proposed_ideas_json=None,
        )
    )

    assert updated.id == created.id
    assert updated.status == AgentRunStatus.COMPLETED
    assert updated.phase == AgentRunPhase.RECIPES
    assert updated.pending_question is None
    fetched = repo.get(created.id)
    assert fetched is not None
    assert fetched.status == AgentRunStatus.COMPLETED


def test_save_round_trips_proposed_ideas_json(session: Session) -> None:
    repo = AgentRunRepository(session)
    fridge_input_id = _fridge_input_id(session)
    ideas_json = '[{"dish_name": "Carrot soup", "description": "Simple soup"}]'

    saved = repo.save(
        AgentRun(
            id=None,
            fridge_input_id=fridge_input_id,
            status=AgentRunStatus.AWAITING_SELECTION,
            phase=AgentRunPhase.IDEAS,
            messages_json="[]",
            pending_question=None,
            proposed_ideas_json=ideas_json,
        )
    )

    assert saved.id is not None
    fetched = repo.get(saved.id)
    assert fetched is not None
    assert fetched.proposed_ideas_json == ideas_json
