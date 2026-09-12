from app.domain.equipment import Equipment
from app.persistence.repositories.equipment_repository import EquipmentRepository
from app.services.exceptions import NotFoundError


class EquipmentService:
    def __init__(self, repository: EquipmentRepository) -> None:
        self._repository = repository

    def list_equipment(self) -> list[Equipment]:
        return self._repository.list_all()

    def add_equipment(self, equipment: Equipment) -> Equipment:
        return self._repository.add(equipment)

    def remove_equipment(self, equipment_id: int) -> None:
        if not self._repository.delete(equipment_id):
            raise NotFoundError(f"Equipment {equipment_id} does not exist.")
