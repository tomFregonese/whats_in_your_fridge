from fastapi import APIRouter, Depends

from app.dependencies import get_suggestion_service
from app.dto.fridge_input_dto import FridgeInputDtoIn
from app.dto.suggestion_dto import SuggestionDtoOut, SuggestionsResultDtoOut
from app.services.suggestion_service import SuggestionService

router = APIRouter(prefix="/suggestions", tags=["suggestions"])


@router.post("")
def create_suggestions(
    dto: FridgeInputDtoIn,
    service: SuggestionService = Depends(get_suggestion_service),
) -> SuggestionsResultDtoOut:
    fridge_input, suggestions = service.generate(dto.to_domain())
    assert fridge_input.id is not None
    return SuggestionsResultDtoOut(
        status="completed",
        fridge_input_id=fridge_input.id,
        suggestions=[SuggestionDtoOut.from_domain(s) for s in suggestions],
    )
