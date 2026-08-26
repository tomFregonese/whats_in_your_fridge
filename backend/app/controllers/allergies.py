from fastapi import APIRouter, Depends

from app.dependencies import get_allergy_service
from app.dto.allergy_dto import AllergyDtoIn, AllergyDtoOut
from app.services.allergy_service import AllergyService

router = APIRouter(prefix="/allergies", tags=["allergies"])


@router.get("")
def list_allergies(service: AllergyService = Depends(get_allergy_service)) -> list[AllergyDtoOut]:
    return [AllergyDtoOut.from_domain(allergy) for allergy in service.list_allergies()]


@router.post("", status_code=201)
def add_allergy(
    dto: AllergyDtoIn,
    service: AllergyService = Depends(get_allergy_service),
) -> AllergyDtoOut:
    return AllergyDtoOut.from_domain(service.add_allergy(dto.to_domain()))


@router.delete("/{allergy_id}", status_code=204)
def delete_allergy(
    allergy_id: int,
    service: AllergyService = Depends(get_allergy_service),
) -> None:
    service.remove_allergy(allergy_id)
