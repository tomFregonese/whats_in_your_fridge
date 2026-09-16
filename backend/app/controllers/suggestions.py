from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from openai.types.chat import ChatCompletionMessageParam
from starlette.requests import Request

from app.agent import prompts
from app.agent.dedup import DedupProvider
from app.dependencies import (
    get_agent_run_repository,
    get_allergy_repository,
    get_dedup_provider,
    get_equipment_repository,
    get_feedback_service,
    get_fridge_input_repository,
    get_fridge_stock_service,
    get_meal_plan_service,
    get_security_service,
    get_settings_service,
    get_suggestion_repository,
    get_suggestion_service,
)
from app.domain.agent_run import AgentRunPhase
from app.dto.dish_idea_dto import DishIdeaDtoOut
from app.dto.feedback_dto import FeedbackDtoIn, FeedbackDtoOut
from app.dto.fridge_input_dto import FridgeInputDtoIn
from app.dto.fridge_stock_dto import FridgeStockItemDtoOut
from app.dto.suggestion_dto import (
    AgendaEntryDtoOut,
    RespondDtoIn,
    SelectDtoIn,
    SuggestionDtoOut,
    SuggestionsResultDtoOut,
    SuggestionUpdateDtoIn,
)
from app.persistence.repositories.agent_run_repository import AgentRunRepository
from app.persistence.repositories.allergy_repository import AllergyRepository
from app.persistence.repositories.equipment_repository import EquipmentRepository
from app.persistence.repositories.fridge_input_repository import FridgeInputRepository
from app.persistence.repositories.suggestion_repository import SuggestionRepository
from app.security.service import SecurityService
from app.services.exceptions import ModelNotConfiguredError, NotFoundError
from app.services.feedback_service import FeedbackService
from app.services.fridge_stock_service import FridgeStockService
from app.services.meal_plan_service import MealPlanService
from app.services.settings_service import SettingsService
from app.services.suggestion_service import (
    ClarificationOutcome,
    IdeasOutcome,
    SuggestionOutcome,
    SuggestionService,
)
from app.streaming_service import deliver_answer, deliver_selection, sse_generator, start_background

router = APIRouter(prefix="/suggestions", tags=["suggestions"])


def _to_dto(fridge_input_id: int, outcome: SuggestionOutcome) -> SuggestionsResultDtoOut:
    if isinstance(outcome, ClarificationOutcome):
        return SuggestionsResultDtoOut(
            status="clarification_needed",
            fridge_input_id=fridge_input_id,
            run_id=outcome.run_id,
            question=outcome.question,
            options=outcome.options,
        )
    if isinstance(outcome, IdeasOutcome):
        return SuggestionsResultDtoOut(
            status="ideas_proposed",
            fridge_input_id=fridge_input_id,
            run_id=outcome.run_id,
            ideas=[
                DishIdeaDtoOut.from_domain(index, idea) for index, idea in enumerate(outcome.ideas)
            ],
            notes_generales=outcome.notes_generales,
        )
    return SuggestionsResultDtoOut(
        status="completed",
        fridge_input_id=fridge_input_id,
        meal_plan_id=outcome.meal_plan_id,
        suggestions=[SuggestionDtoOut.from_domain(s) for s in outcome.suggestions],
        notes_generales=outcome.notes_generales,
        removed_stock_items=[
            FridgeStockItemDtoOut.from_domain(item) for item in outcome.removed_stock_items
        ],
        agenda=[AgendaEntryDtoOut.from_domain(entry) for entry in outcome.agenda],
    )


@router.post("")
def create_suggestions(
    dto: FridgeInputDtoIn,
    service: SuggestionService = Depends(get_suggestion_service),
) -> SuggestionsResultDtoOut:
    fridge_input_id, outcome = service.generate(dto.to_domain())
    return _to_dto(fridge_input_id, outcome)


@router.post("/runs/{run_id}/respond")
def respond_to_clarification(
    run_id: int,
    dto: RespondDtoIn,
    service: SuggestionService = Depends(get_suggestion_service),
) -> SuggestionsResultDtoOut:
    fridge_input_id, outcome = service.respond(run_id, dto.answer)
    return _to_dto(fridge_input_id, outcome)


@router.post("/runs/{run_id}/select")
def select_ideas(
    run_id: int,
    dto: SelectDtoIn,
    service: SuggestionService = Depends(get_suggestion_service),
) -> SuggestionsResultDtoOut:
    fridge_input_id, outcome = service.select(run_id, dto.selected_indexes)
    return _to_dto(fridge_input_id, outcome)


# ---------------------------------------------------------------------------
# Streaming entry point
# POST /api/suggestions/stream — kicks off a background generation and
# returns the run_id so the client can connect to GET /runs/{id}/events
# for SSE.
# ---------------------------------------------------------------------------


@router.post("/stream", status_code=202)
def create_suggestions_stream(
    dto: FridgeInputDtoIn,
    request: Request,
    fridge_input_repository: FridgeInputRepository = Depends(get_fridge_input_repository),
    agent_run_repository: AgentRunRepository = Depends(get_agent_run_repository),
    suggestion_repository: SuggestionRepository = Depends(get_suggestion_repository),
    allergy_repository: AllergyRepository = Depends(get_allergy_repository),
    equipment_repository: EquipmentRepository = Depends(get_equipment_repository),
    settings_service: SettingsService = Depends(get_settings_service),
    security_service: SecurityService = Depends(get_security_service),
    dedup_provider: DedupProvider = Depends(get_dedup_provider),
    fridge_stock_service: FridgeStockService = Depends(get_fridge_stock_service),
) -> dict[str, int]:
    fridge_input = dto.to_domain()
    saved_input = fridge_input_repository.add(fridge_input)
    assert saved_input.id is not None

    settings = settings_service.get_settings()
    if settings.openrouter_model_id is None:
        raise ModelNotConfiguredError("No OpenRouter model has been selected yet.")

    token = security_service.get_token()

    system_prompt = prompts.build_system_prompt(
        default_servings=settings.default_servings,
        allergies=allergy_repository.list_all(),
        equipment=equipment_repository.list_all(),
        preferences=[],
        dedup_context=dedup_provider.get_exclusion_context(),
        phase=AgentRunPhase.IDEAS,
        sourcing_mode=saved_input.sourcing_mode,
        mode=saved_input.mode,
        days=saved_input.days,
    )
    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompts.build_user_message(saved_input)},
    ]

    allergies = allergy_repository.list_all()
    equipment = equipment_repository.list_all()

    run_id = saved_input.id  # reuse the fridge_input id as the streaming run id

    start_background(
        run_id=run_id,
        fridge_input=saved_input,
        messages=messages,
        token=token,
        model=settings.openrouter_model_id,
        allergies=allergies,
        equipment=equipment,
        fridge_input_repository=fridge_input_repository,
        agent_run_repository=agent_run_repository,
        suggestion_repository=suggestion_repository,
        settings_service=settings_service,
        security_service=security_service,
        dedup_provider=dedup_provider,
        fridge_stock_service=fridge_stock_service,
    )

    return {"run_id": run_id}


# ---------------------------------------------------------------------------
# SSE event stream
# GET /api/suggestions/runs/{run_id}/events
# ---------------------------------------------------------------------------


@router.get("/runs/{run_id}/events")
async def stream_events(run_id: int) -> StreamingResponse:
    return StreamingResponse(
        sse_generator(run_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Clarification answer in streaming mode
# POST /api/suggestions/runs/{run_id}/respond-stream
# ---------------------------------------------------------------------------


@router.post("/runs/{run_id}/respond-stream")
def respond_stream(run_id: int, dto: RespondDtoIn) -> dict[str, str]:
    try:
        deliver_answer(run_id, dto.answer)
    except NotFoundError as exc:
        detail = f"No active streaming session for run {run_id}."
        raise HTTPException(status_code=404, detail=detail) from exc
    return {"status": "accepted"}


# ---------------------------------------------------------------------------
# Dish selection in streaming mode
# POST /api/suggestions/runs/{run_id}/select-stream
# ---------------------------------------------------------------------------


@router.post("/runs/{run_id}/select-stream")
def select_stream(run_id: int, dto: SelectDtoIn) -> dict[str, str]:
    try:
        deliver_selection(run_id, dto.selected_indexes)
    except NotFoundError as exc:
        detail = f"No active streaming session for run {run_id}."
        raise HTTPException(status_code=404, detail=detail) from exc
    return {"status": "accepted"}


@router.patch("/{suggestion_id}")
def update_suggestion(
    suggestion_id: int,
    dto: SuggestionUpdateDtoIn,
    service: MealPlanService = Depends(get_meal_plan_service),
) -> SuggestionDtoOut:
    """Backs the meal-plan table's inline edit (dish name, portions, and the
    leftover-transformation note) — see `MealPlanService.update_suggestion`.
    """
    return SuggestionDtoOut.from_domain(
        service.update_suggestion(
            suggestion_id,
            dish_name=dto.dish_name,
            servings=dto.servings,
            leftover_transformation=dto.leftover_transformation,
        )
    )


@router.post("/{suggestion_id}/feedback", status_code=201)
def add_feedback(
    suggestion_id: int,
    dto: FeedbackDtoIn,
    service: FeedbackService = Depends(get_feedback_service),
) -> FeedbackDtoOut:
    return FeedbackDtoOut.from_domain(
        service.save(suggestion_id, liked=dto.liked, comment=dto.comment)
    )
