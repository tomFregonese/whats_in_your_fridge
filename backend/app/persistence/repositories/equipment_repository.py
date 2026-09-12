from sqlmodel import Session, select

from app.domain.equipment import Equipment
from app.persistence.entities.equipment_entity import EquipmentEntity


class EquipmentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_all(self) -> list[Equipment]:
        entities = self._session.exec(
            select(EquipmentEntity).order_by(EquipmentEntity.name)
        ).all()
        return [entity.to_domain() for entity in entities]

    def add(self, equipment: Equipment) -> Equipment:
        entity = EquipmentEntity.from_domain(equipment)
        self._session.add(entity)
        self._session.commit()
        self._session.refresh(entity)
        return entity.to_domain()

    def delete(self, equipment_id: int) -> bool:
        """Returns True if a row was deleted, False if `equipment_id` didn't exist."""
        entity = self._session.get(EquipmentEntity, equipment_id)
        if entity is None:
            return False
        self._session.delete(entity)
        self._session.commit()
        return True
