from __future__ import annotations

from sqlmodel import Field, SQLModel

from app.domain.agent_run import AgentRun, AgentRunPhase, AgentRunStatus


class AgentRunEntity(SQLModel, table=True):
    __tablename__ = "agent_run"

    id: int | None = Field(default=None, primary_key=True)
    fridge_input_id: int = Field(foreign_key="fridge_input.id", index=True)
    status: str
    phase: str
    messages_json: str
    pending_question: str | None = None
    proposed_ideas_json: str | None = None

    def to_domain(self) -> AgentRun:
        return AgentRun(
            id=self.id,
            fridge_input_id=self.fridge_input_id,
            status=AgentRunStatus(self.status),
            phase=AgentRunPhase(self.phase),
            messages_json=self.messages_json,
            pending_question=self.pending_question,
            proposed_ideas_json=self.proposed_ideas_json,
        )

    @classmethod
    def from_domain(cls, agent_run: AgentRun) -> AgentRunEntity:
        return cls(
            id=agent_run.id,
            fridge_input_id=agent_run.fridge_input_id,
            status=agent_run.status.value,
            phase=agent_run.phase.value,
            messages_json=agent_run.messages_json,
            pending_question=agent_run.pending_question,
            proposed_ideas_json=agent_run.proposed_ideas_json,
        )
