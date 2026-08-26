from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AgentRunStatus(StrEnum):
    RUNNING = "running"
    AWAITING_CLARIFICATION = "awaiting_clarification"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class AgentRun:
    """State of one agent tool-calling conversation for a `FridgeInput`.

    `messages_json` holds the raw message history sent to/received from the
    LLM, so the loop can resume after a `demander_precision` round-trip
    (see `app.agent.loop`).
    """

    id: int | None
    fridge_input_id: int
    status: AgentRunStatus
    messages_json: str
    pending_question: str | None
