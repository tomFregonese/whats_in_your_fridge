from fastapi import APIRouter, Depends

from app.dependencies import get_suggestion_service
from app.dto.fridge_input_dto import FridgeInputDtoIn
from app.dto.suggestion_dto import RespondDtoIn, SuggestionDtoOut, SuggestionsResultDtoOut
from app.services.suggestion_service import (
    ClarificationOutcome,
    SuggestionOutcome,
    SuggestionService,
)

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
    suggestions = [SuggestionDtoOut.from_domain(plat.to_domain()) for plat in outcome.plats.plats]
    return SuggestionsResultDtoOut(
        status="completed",
        fridge_input_id=fridge_input_id,
        suggestions=suggestions,
        notes_generales=outcome.plats.notes_generales,
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
