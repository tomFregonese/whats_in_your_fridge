from sqlmodel import Session

from app.domain.agent_run import AgentRun
from app.persistence.entities.agent_run_entity import AgentRunEntity


class AgentRunRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, run_id: int) -> AgentRun | None:
        entity = self._session.get(AgentRunEntity, run_id)
        return entity.to_domain() if entity is not None else None

    def save(self, agent_run: AgentRun) -> AgentRun:
        """Creates a new row if `agent_run.id` is unset, else updates the
        existing one in place — the same upsert convention as
        `SettingsRepository`.
        """
        entity: AgentRunEntity
        if agent_run.id is None:
            entity = AgentRunEntity.from_domain(agent_run)
            self._session.add(entity)
        else:
            existing = self._session.get(AgentRunEntity, agent_run.id)
            if existing is None:
                raise ValueError(f"AgentRun {agent_run.id} does not exist.")
            existing.status = agent_run.status.value
            existing.phase = agent_run.phase.value
            existing.messages_json = agent_run.messages_json
            existing.pending_question = agent_run.pending_question
            existing.proposed_ideas_json = agent_run.proposed_ideas_json
            entity = existing

        self._session.commit()
        self._session.refresh(entity)
        return entity.to_domain()
