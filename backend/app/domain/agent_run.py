from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AgentRunStatus(StrEnum):
    RUNNING = "running"
    AWAITING_CLARIFICATION = "awaiting_clarification"
    AWAITING_SELECTION = "awaiting_selection"
    COMPLETED = "completed"
    ERROR = "error"


class AgentRunPhase(StrEnum):
    """Which of the two agent tool-calling phases this run is in — decides
    which tool set is offered on resume (see `app.agent.loop`/`agent.tools`)
    and what a pending `AWAITING_CLARIFICATION` is actually about, since
    that status is now shared by both phases.
    """

    IDEAS = "ideas"
    RECIPES = "recipes"


@dataclass
class AgentRun:
    """State of one agent tool-calling conversation for a `FridgeInput`.

    `messages_json` holds the raw message history sent to/received from the
    LLM, so the loop can resume after a `demander_precision` round-trip
    (see `app.agent.loop`). `proposed_ideas_json` serves the same
    "ephemeral, single round-trip" role as `pending_question` (not a
    persisted domain concept of its own), but its meaning depends on
    `phase`/`status`: during `IDEAS`-phase `AWAITING_SELECTION`, every
    candidate the user can pick from; during a `RECIPES`-phase
    `AWAITING_CLARIFICATION`, only the confirmed selection those recipes
    are being generated for (so a `respond()` resume still knows
    `selected_dish_names` — see `services/suggestion_service.py`).
    """

    id: int | None
    fridge_input_id: int
    status: AgentRunStatus
    phase: AgentRunPhase
    messages_json: str
    pending_question: str | None
    proposed_ideas_json: str | None
