from sqlmodel import Session, select

from app.domain.allergy import Allergy
from app.persistence.entities.allergy_entity import AllergyEntity


class AllergyRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_all(self) -> list[Allergy]:
        entities = self._session.exec(
            select(AllergyEntity).order_by(AllergyEntity.ingredient_name)
        ).all()
        return [entity.to_domain() for entity in entities]

    def add(self, allergy: Allergy) -> Allergy:
        entity = AllergyEntity.from_domain(allergy)
        self._session.add(entity)
        self._session.commit()
        self._session.refresh(entity)
        return entity.to_domain()

    def delete(self, allergy_id: int) -> bool:
        """Returns True if a row was deleted, False if `allergy_id` didn't exist."""
        entity = self._session.get(AllergyEntity, allergy_id)
        if entity is None:
            return False
        self._session.delete(entity)
        self._session.commit()
        return True
