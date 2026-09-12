from fastapi import APIRouter, Depends

from app.dependencies import get_equipment_service
from app.dto.equipment_dto import EquipmentDtoIn, EquipmentDtoOut
from app.services.equipment_service import EquipmentService

router = APIRouter(prefix="/equipment", tags=["equipment"])


@router.get("")
def list_equipment(
    service: EquipmentService = Depends(get_equipment_service),
) -> list[EquipmentDtoOut]:
    return [EquipmentDtoOut.from_domain(equipment) for equipment in service.list_equipment()]


@router.post("", status_code=201)
def add_equipment(
    dto: EquipmentDtoIn,
    service: EquipmentService = Depends(get_equipment_service),
) -> EquipmentDtoOut:
    return EquipmentDtoOut.from_domain(service.add_equipment(dto.to_domain()))


@router.delete("/{equipment_id}", status_code=204)
def delete_equipment(
    equipment_id: int,
    service: EquipmentService = Depends(get_equipment_service),
) -> None:
    service.remove_equipment(equipment_id)
