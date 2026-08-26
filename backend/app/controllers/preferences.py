from fastapi import APIRouter, Depends

from app.dependencies import get_preference_service
from app.dto.preference_dto import PreferenceNoteDtoIn, PreferenceNoteDtoOut
from app.services.preference_service import PreferenceService

router = APIRouter(prefix="/preferences", tags=["preferences"])


@router.get("")
def list_preferences(
    service: PreferenceService = Depends(get_preference_service),
) -> list[PreferenceNoteDtoOut]:
    return [PreferenceNoteDtoOut.from_domain(note) for note in service.list_preferences()]


@router.post("", status_code=201)
def add_preference(
    dto: PreferenceNoteDtoIn,
    service: PreferenceService = Depends(get_preference_service),
) -> PreferenceNoteDtoOut:
    return PreferenceNoteDtoOut.from_domain(service.add_preference(dto.to_domain()))


@router.delete("/{preference_id}", status_code=204)
def delete_preference(
    preference_id: int,
    service: PreferenceService = Depends(get_preference_service),
) -> None:
    service.remove_preference(preference_id)
