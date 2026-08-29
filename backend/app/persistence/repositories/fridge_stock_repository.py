from datetime import UTC, datetime

from sqlalchemy import ColumnElement, func
from sqlmodel import Session, select

from app.domain.fridge_stock import FridgeStockItem
from app.persistence.entities.fridge_stock_item_entity import FridgeStockItemEntity


class FridgeStockRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_all(self) -> list[FridgeStockItem]:
        entities = self._session.exec(
            select(FridgeStockItemEntity).order_by(FridgeStockItemEntity.ingredient_name)
        ).all()
        return [entity.to_domain() for entity in entities]

    def get(self, item_id: int) -> FridgeStockItem | None:
        entity = self._session.get(FridgeStockItemEntity, item_id)
        return entity.to_domain() if entity is not None else None

    def get_many(self, ids: list[int]) -> list[FridgeStockItem]:
        """Used by deduction (`FridgeStockService.deduct`) to report back
        what's about to be removed before it's gone."""
        if not ids:
            return []
        condition: ColumnElement[bool] = (
            FridgeStockItemEntity.id.in_(ids)  # type: ignore[union-attr]
        )
        entities = self._session.exec(select(FridgeStockItemEntity).where(condition)).all()
        return [entity.to_domain() for entity in entities]

    def find_by_name(self, name: str) -> FridgeStockItem | None:
        """Case-insensitive exact match — used by voice dictation
        (`FridgeStockService.upsert_dictated_items`) to update an existing
        item's quantity instead of creating a duplicate."""
        condition: ColumnElement[bool] = (
            func.lower(FridgeStockItemEntity.ingredient_name) == name.strip().lower()
        )
        entity = self._session.exec(select(FridgeStockItemEntity).where(condition)).first()
        return entity.to_domain() if entity is not None else None

    def add(self, item: FridgeStockItem) -> FridgeStockItem:
        entity = FridgeStockItemEntity.from_domain(item)
        self._session.add(entity)
        self._session.commit()
        self._session.refresh(entity)
        return entity.to_domain()

    def update(
        self,
        item_id: int,
        *,
        ingredient_name: str,
        quantity_value: float | None,
        quantity_unit: str | None,
        quantity_raw: str | None,
    ) -> FridgeStockItem | None:
        """Mutates the row in place and bumps `updated_at`. Returns `None`
        if `item_id` doesn't exist — same "None on missing" convention as
        `get()`, rather than raising (the service layer decides whether
        that's a 404)."""
        entity = self._session.get(FridgeStockItemEntity, item_id)
        if entity is None:
            return None
        entity.ingredient_name = ingredient_name
        entity.quantity_value = quantity_value
        entity.quantity_unit = quantity_unit
        entity.quantity_raw = quantity_raw
        entity.updated_at = datetime.now(UTC)
        self._session.add(entity)
        self._session.commit()
        self._session.refresh(entity)
        return entity.to_domain()

    def delete(self, item_id: int) -> bool:
        """Returns True if a row was deleted, False if `item_id` didn't exist."""
        entity = self._session.get(FridgeStockItemEntity, item_id)
        if entity is None:
            return False
        self._session.delete(entity)
        self._session.commit()
        return True

    def delete_many(self, ids: list[int]) -> None:
        if not ids:
            return
        condition: ColumnElement[bool] = (
            FridgeStockItemEntity.id.in_(ids)  # type: ignore[union-attr]
        )
        entities = self._session.exec(select(FridgeStockItemEntity).where(condition)).all()
        for entity in entities:
            self._session.delete(entity)
        self._session.commit()
