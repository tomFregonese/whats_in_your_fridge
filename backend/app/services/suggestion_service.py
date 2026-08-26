"""Orchestrates one fridge-input submission end to end: persists the
input, builds the agent's conversation, runs the tool-calling loop, and
persists `agent_run` state across clarification round-trips.

Not part of this milestone (see the project plan — later milestones add
each of these around the same loop without changing its shape):
allergy checking, dedup/recent-meals context, model-availability check,
and meal_plan/suggestion persistence (results are returned as-is, not
saved yet).
"""

from dataclasses import dataclass

from openai.types.chat import ChatCompletionMessageParam

from app.agent import loop, prompts
from app.agent.output_schema import ProposerPlatsArgs
from app.domain.agent_run import AgentRun, AgentRunStatus
from app.domain.fridge_input import FridgeInput
from app.persistence.repositories.agent_run_repository import AgentRunRepository
from app.persistence.repositories.allergy_repository import AllergyRepository
from app.persistence.repositories.fridge_input_repository import FridgeInputRepository
from app.persistence.repositories.preference_note_repository import PreferenceNoteRepository
from app.security.service import SecurityService
from app.services.exceptions import ModelNotConfiguredError, NotFoundError
from app.services.settings_service import SettingsService


@dataclass
class ClarificationOutcome:
    run_id: int
    question: str
    options: list[str] | None


@dataclass
class CompletedOutcome:
    plats: ProposerPlatsArgs


SuggestionOutcome = ClarificationOutcome | CompletedOutcome


class SuggestionService:
    def __init__(
        self,
        fridge_input_repository: FridgeInputRepository,
        agent_run_repository: AgentRunRepository,
        allergy_repository: AllergyRepository,
        preference_repository: PreferenceNoteRepository,
        settings_service: SettingsService,
        security_service: SecurityService,
    ) -> None:
        self._fridge_input_repository = fridge_input_repository
        self._agent_run_repository = agent_run_repository
        self._allergy_repository = allergy_repository
        self._preference_repository = preference_repository
        self._settings_service = settings_service
        self._security_service = security_service

    def generate(self, fridge_input: FridgeInput) -> tuple[int, SuggestionOutcome]:
        saved_input = self._fridge_input_repository.add(fridge_input)
        assert saved_input.id is not None

        settings = self._settings_service.get_settings()
        system_prompt = prompts.build_system_prompt(
            default_servings=settings.default_servings,
            allergies=self._allergy_repository.list_all(),
            preferences=self._preference_repository.list_all(),
        )
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompts.build_user_message(saved_input)},
        ]

        outcome = self._run_loop(fridge_input_id=saved_input.id, messages=messages)
        return saved_input.id, outcome

    def respond(self, run_id: int, answer: str) -> tuple[int, SuggestionOutcome]:
        agent_run = self._agent_run_repository.get(run_id)
        if agent_run is None:
            raise NotFoundError(f"Agent run {run_id} does not exist.")

        messages = loop.deserialize_messages(agent_run.messages_json)
        tool_call_id = loop.pending_tool_call_id(messages)
        messages.append(loop.build_tool_result_message(tool_call_id, answer))

        outcome = self._run_loop(
            fridge_input_id=agent_run.fridge_input_id,
            messages=messages,
            existing_run_id=run_id,
        )
        return agent_run.fridge_input_id, outcome

    def _run_loop(
        self,
        *,
        fridge_input_id: int,
        messages: list[ChatCompletionMessageParam],
        existing_run_id: int | None = None,
    ) -> SuggestionOutcome:
        token = self._security_service.get_token()
        settings = self._settings_service.get_settings()
        if settings.openrouter_model_id is None:
            raise ModelNotConfiguredError("No OpenRouter model has been selected yet.")

        result = loop.run(token=token, model=settings.openrouter_model_id, messages=messages)

        if isinstance(result, loop.ClarificationNeeded):
            saved_run = self._agent_run_repository.save(
                AgentRun(
                    id=existing_run_id,
                    fridge_input_id=fridge_input_id,
                    status=AgentRunStatus.AWAITING_CLARIFICATION,
                    messages_json=loop.serialize_messages(result.messages),
                    pending_question=result.question,
                )
            )
            assert saved_run.id is not None
            return ClarificationOutcome(
                run_id=saved_run.id, question=result.question, options=result.options
            )

        if existing_run_id is not None:
            existing = self._agent_run_repository.get(existing_run_id)
            assert existing is not None
            self._agent_run_repository.save(
                AgentRun(
                    id=existing_run_id,
                    fridge_input_id=fridge_input_id,
                    status=AgentRunStatus.COMPLETED,
                    messages_json=existing.messages_json,
                    pending_question=None,
                )
            )

        return CompletedOutcome(plats=result.args)
