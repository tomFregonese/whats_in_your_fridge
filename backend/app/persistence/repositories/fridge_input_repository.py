from dataclasses import replace

from sqlalchemy import ColumnElement
from sqlmodel import Session, select

from app.domain.fridge_input import FridgeInput
from app.persistence.entities.fridge_input_entity import (
    FridgeInputEntity,
    FridgeInputItemEntity,
)


class FridgeInputRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, fridge_input_id: int) -> FridgeInput | None:
        entity = self._session.get(FridgeInputEntity, fridge_input_id)
        if entity is None:
            return None

        # Same class-level field access typing gap noted elsewhere.
        condition: ColumnElement[bool] = (
            FridgeInputItemEntity.fridge_input_id == fridge_input_id  # type: ignore[assignment]
        )
        item_entities = self._session.exec(select(FridgeInputItemEntity).where(condition)).all()

        result = entity.to_domain()
        result.items = [item_entity.to_domain() for item_entity in item_entities]
        return result

    def add(self, fridge_input: FridgeInput) -> FridgeInput:
        """Persists the parent row, then each item against its real id —
        the aggregate assembly the domain model's docstring describes.
        """
        entity = FridgeInputEntity.from_domain(fridge_input)
        self._session.add(entity)
        self._session.flush()  # assigns entity.id without committing yet
        assert entity.id is not None

        item_entities = [
            FridgeInputItemEntity.from_domain(replace(item, fridge_input_id=entity.id))
            for item in fridge_input.items
        ]
        for item_entity in item_entities:
            self._session.add(item_entity)

        self._session.commit()
        self._session.refresh(entity)
        for item_entity in item_entities:
            self._session.refresh(item_entity)

        result = entity.to_domain()
        result.items = [item_entity.to_domain() for item_entity in item_entities]
        return result
