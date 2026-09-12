"""Orchestrates one fridge-input submission end to end, across both agent
phases (see `AgentRunPhase`): persists the input, builds the `IDEAS`-phase
conversation (allergies, preferences, and a recent-meals dedup context —
see `agent/dedup.py`), defensively checks the configured model is still
live before spending a request on it, runs the `IDEAS` tool-calling loop,
and persists the proposed shortlist on `agent_run` so the user can pick
from it (`select()`). Once a selection is confirmed, runs the `RECIPES`
loop (allergy-checked — see `agent/allergy_check.py`) for exactly the
picked dish(es), and — once that completes — persists the result as a
`meal_plan`/`suggestion` aggregate (see `SuggestionRepository`), which is
also what makes `dedup_provider` see real history from the next
generation onward.

`notes_generales` (the LLM's free-text remarks, e.g. noting a dropped
allergenic dish) is deliberately *not* persisted — there's no column for
it on `meal_plan` (see the project plan's schema) — so it's only present
on the response of the call that produced it, not on later reads of the
same plan via `GET /api/meal-plans/{id}`.
"""

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime

from openai.types.chat import ChatCompletionMessageParam

from app.agent import loop, prompts
from app.agent.catalog import is_model_available
from app.agent.dedup import DedupProvider
from app.domain.agent_run import AgentRun, AgentRunPhase, AgentRunStatus
from app.domain.dish_idea import DishIdea
from app.domain.fridge_input import FridgeInput, FridgeInputMode
from app.domain.fridge_stock import FridgeStockItem
from app.domain.suggestion import AgendaEntry, MealPlan, Suggestion
from app.persistence.repositories.agent_run_repository import AgentRunRepository
from app.persistence.repositories.allergy_repository import AllergyRepository
from app.persistence.repositories.equipment_repository import EquipmentRepository
from app.persistence.repositories.fridge_input_repository import FridgeInputRepository
from app.persistence.repositories.preference_note_repository import PreferenceNoteRepository
from app.persistence.repositories.suggestion_repository import SuggestionRepository
from app.security.service import SecurityService
from app.services.exceptions import (
    ModelNotConfiguredError,
    ModelUnavailableError,
    NotFoundError,
)
from app.services.fridge_stock_service import FridgeStockService
from app.services.meal_agenda_service import DishForAgenda, build_agenda
from app.services.settings_service import SettingsService


@dataclass
class ClarificationOutcome:
    run_id: int
    question: str
    options: list[str] | None


@dataclass
class IdeasOutcome:
    run_id: int
    ideas: list[DishIdea]
    notes_generales: str | None


@dataclass
class CompletedOutcome:
    meal_plan_id: int
    suggestions: list[Suggestion]
    notes_generales: str | None
    removed_stock_items: list[FridgeStockItem] = field(default_factory=list)
    agenda: list[AgendaEntry] = field(default_factory=list)


SuggestionOutcome = ClarificationOutcome | IdeasOutcome | CompletedOutcome


class SuggestionService:
    def __init__(
        self,
        fridge_input_repository: FridgeInputRepository,
        agent_run_repository: AgentRunRepository,
        suggestion_repository: SuggestionRepository,
        allergy_repository: AllergyRepository,
        equipment_repository: EquipmentRepository,
        preference_repository: PreferenceNoteRepository,
        settings_service: SettingsService,
        security_service: SecurityService,
        dedup_provider: DedupProvider,
        fridge_stock_service: FridgeStockService,
    ) -> None:
        self._fridge_input_repository = fridge_input_repository
        self._agent_run_repository = agent_run_repository
        self._suggestion_repository = suggestion_repository
        self._allergy_repository = allergy_repository
        self._equipment_repository = equipment_repository
        self._preference_repository = preference_repository
        self._settings_service = settings_service
        self._security_service = security_service
        self._dedup_provider = dedup_provider
        self._fridge_stock_service = fridge_stock_service

    def generate(self, fridge_input: FridgeInput) -> tuple[int, SuggestionOutcome]:
        saved_input = self._fridge_input_repository.add(fridge_input)
        assert saved_input.id is not None

        system_prompt = prompts.build_system_prompt(
            default_servings=self._settings_service.get_settings().default_servings,
            allergies=self._allergy_repository.list_all(),
            equipment=self._equipment_repository.list_all(),
            preferences=self._preference_repository.list_all(),
            dedup_context=self._dedup_provider.get_exclusion_context(),
            phase=AgentRunPhase.IDEAS,
            sourcing_mode=saved_input.sourcing_mode,
            mode=saved_input.mode,
            days=fridge_input.days,
        )
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompts.build_user_message(saved_input)},
        ]

        outcome = self._run_ideas_phase(fridge_input_id=saved_input.id, messages=messages)
        return saved_input.id, outcome

    def respond(self, run_id: int, answer: str) -> tuple[int, SuggestionOutcome]:
        agent_run = self._agent_run_repository.get(run_id)
        if agent_run is None:
            raise NotFoundError(f"Agent run {run_id} does not exist.")

        fridge_input = self._fridge_input_repository.get(agent_run.fridge_input_id)
        if fridge_input is None:
            raise NotFoundError(f"Fridge input {agent_run.fridge_input_id} does not exist.")

        messages = loop.deserialize_messages(agent_run.messages_json)
        tool_call_id = loop.pending_tool_call_id(messages)
        messages.append(loop.build_tool_result_message(tool_call_id, answer))

        if agent_run.phase == AgentRunPhase.IDEAS:
            outcome = self._run_ideas_phase(
                fridge_input_id=agent_run.fridge_input_id,
                messages=messages,
                existing_run_id=run_id,
            )
        else:
            selected_dish_names = [
                idea.dish_name for idea in self._decode_ideas(agent_run.proposed_ideas_json)
            ]
            outcome = self._run_recipes_phase(
                fridge_input_id=agent_run.fridge_input_id,
                messages=messages,
                selected_dish_names=selected_dish_names,
                existing_run_id=run_id,
            )
        return agent_run.fridge_input_id, outcome

    def select(self, run_id: int, selected_indexes: list[int]) -> tuple[int, SuggestionOutcome]:
        """Resumes an `AWAITING_SELECTION` run: turns the user's picks (by
        `DishIdeaDtoOut.index`) into a tool result for the pending
        `proposer_idees` call, then runs the `RECIPES` phase for exactly
        those dishes."""
        agent_run = self._agent_run_repository.get(run_id)
        if agent_run is None:
            raise NotFoundError(f"Agent run {run_id} does not exist.")

        all_ideas = self._decode_ideas(agent_run.proposed_ideas_json)
        if any(i < 0 or i >= len(all_ideas) for i in selected_indexes):
            raise NotFoundError(
                f"Agent run {run_id} has no idea at one of indexes {selected_indexes}."
            )
        selected = [all_ideas[i] for i in selected_indexes]

        messages = loop.deserialize_messages(agent_run.messages_json)
        tool_call_id = loop.pending_tool_call_id(messages)
        names = ", ".join(f'"{idea.dish_name}"' for idea in selected)
        content = (
            f"The user selected: {names}. Call `proposer_plats` now with the full recipe "
            "for exactly these dishes, in this order, and no others."
        )
        messages.append(loop.build_tool_result_message(tool_call_id, content))

        outcome = self._run_recipes_phase(
            fridge_input_id=agent_run.fridge_input_id,
            messages=messages,
            selected_dish_names=[idea.dish_name for idea in selected],
            existing_run_id=run_id,
        )
        return agent_run.fridge_input_id, outcome

    def _run_ideas_phase(
        self,
        *,
        fridge_input_id: int,
        messages: list[ChatCompletionMessageParam],
        existing_run_id: int | None = None,
    ) -> SuggestionOutcome:
        token, model = self._token_and_model()
        result = loop.run_ideas(token=token, model=model, messages=messages)

        if isinstance(result, loop.ClarificationNeeded):
            saved_run = self._agent_run_repository.save(
                AgentRun(
                    id=existing_run_id,
                    fridge_input_id=fridge_input_id,
                    status=AgentRunStatus.AWAITING_CLARIFICATION,
                    phase=AgentRunPhase.IDEAS,
                    messages_json=loop.serialize_messages(result.messages),
                    pending_question=result.question,
                    proposed_ideas_json=None,
                )
            )
            assert saved_run.id is not None
            return ClarificationOutcome(
                run_id=saved_run.id, question=result.question, options=result.options
            )

        saved_run = self._agent_run_repository.save(
            AgentRun(
                id=existing_run_id,
                fridge_input_id=fridge_input_id,
                status=AgentRunStatus.AWAITING_SELECTION,
                phase=AgentRunPhase.IDEAS,
                messages_json=loop.serialize_messages(result.messages),
                pending_question=None,
                proposed_ideas_json=self._encode_ideas(result.ideas),
            )
        )
        assert saved_run.id is not None
        return IdeasOutcome(
            run_id=saved_run.id, ideas=result.ideas, notes_generales=result.notes_generales
        )

    def _run_recipes_phase(
        self,
        *,
        fridge_input_id: int,
        messages: list[ChatCompletionMessageParam],
        selected_dish_names: list[str],
        existing_run_id: int,
    ) -> SuggestionOutcome:
        fridge_input = self._fridge_input_repository.get(fridge_input_id)
        assert fridge_input is not None
        known_stock_item_ids = {
            item.fridge_stock_item_id
            for item in fridge_input.items
            if item.fridge_stock_item_id is not None
        }

        token, model = self._token_and_model()
        result = loop.run(
            token=token,
            model=model,
            messages=messages,
            allergies=self._allergy_repository.list_all(),
            equipment=self._equipment_repository.list_all(),
            sourcing_mode=fridge_input.sourcing_mode,
            selected_dish_names=selected_dish_names,
            known_stock_item_ids=known_stock_item_ids,
        )

        if isinstance(result, loop.ClarificationNeeded):
            saved_run = self._agent_run_repository.save(
                AgentRun(
                    id=existing_run_id,
                    fridge_input_id=fridge_input_id,
                    status=AgentRunStatus.AWAITING_CLARIFICATION,
                    phase=AgentRunPhase.RECIPES,
                    messages_json=loop.serialize_messages(result.messages),
                    pending_question=result.question,
                    # The confirmed selection, not the original candidates
                    # — kept so a further `respond()` resume still knows
                    # which dishes the recipe call is for.
                    proposed_ideas_json=self._encode_ideas(
                        [DishIdea(dish_name=name, description="") for name in selected_dish_names]
                    ),
                )
            )
            assert saved_run.id is not None
            return ClarificationOutcome(
                run_id=saved_run.id, question=result.question, options=result.options
            )

        existing = self._agent_run_repository.get(existing_run_id)
        assert existing is not None
        self._agent_run_repository.save(
            AgentRun(
                id=existing_run_id,
                fridge_input_id=fridge_input_id,
                status=AgentRunStatus.COMPLETED,
                phase=AgentRunPhase.RECIPES,
                messages_json=existing.messages_json,
                pending_question=None,
                proposed_ideas_json=None,
            )
        )

        saved_meal_plan = self._suggestion_repository.add(
            MealPlan(
                id=None,
                fridge_input_id=fridge_input_id,
                mode=fridge_input.mode,
                created_at=datetime.now(UTC),
                suggestions=result.suggestions,
            )
        )
        assert saved_meal_plan.id is not None

        used_stock_ids = sorted(
            {
                stock_id
                for suggestion in saved_meal_plan.suggestions
                for stock_id in json.loads(suggestion.used_stock_item_ids_json)
            }
        )
        removed_items = (
            self._fridge_stock_service.deduct(used_stock_ids) if used_stock_ids else []
        )

        agenda: list[AgendaEntry] = []
        if fridge_input.mode == FridgeInputMode.BATCH and fridge_input.days is not None:
            freezer_capacity_slots = self._settings_service.get_settings().freezer_capacity_slots
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
            agenda = self._suggestion_repository.add_agenda(saved_meal_plan.id, built)

        return CompletedOutcome(
            meal_plan_id=saved_meal_plan.id,
            suggestions=saved_meal_plan.suggestions,
            removed_stock_items=removed_items,
            notes_generales=result.notes_generales,
            agenda=agenda,
        )

    def _token_and_model(self) -> tuple[str, str]:
        token = self._security_service.get_token()
        settings = self._settings_service.get_settings()
        if settings.openrouter_model_id is None:
            raise ModelNotConfiguredError("No OpenRouter model has been selected yet.")
        if not is_model_available(settings.openrouter_model_id):
            raise ModelUnavailableError(
                f"'{settings.openrouter_model_id}' is no longer available in OpenRouter's "
                "`:free` catalog — pick a different model in Settings."
            )
        return token, settings.openrouter_model_id

    @staticmethod
    def _encode_ideas(ideas: list[DishIdea]) -> str:
        return json.dumps(
            [{"dish_name": idea.dish_name, "description": idea.description} for idea in ideas]
        )

    @staticmethod
    def _decode_ideas(raw: str | None) -> list[DishIdea]:
        if raw is None:
            return []
        return [
            DishIdea(dish_name=item["dish_name"], description=item["description"])
            for item in json.loads(raw)
        ]
