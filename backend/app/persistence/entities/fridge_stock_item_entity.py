from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel

from app.domain.fridge_stock import FridgeStockItem


class FridgeStockItemEntity(SQLModel, table=True):
    __tablename__ = "fridge_stock_item"

    id: int | None = Field(default=None, primary_key=True)
    ingredient_name: str = Field(index=True)
    quantity_value: float | None = None
    quantity_unit: str | None = None
    quantity_raw: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def to_domain(self) -> FridgeStockItem:
        return FridgeStockItem(
            id=self.id,
            ingredient_name=self.ingredient_name,
            quantity_value=self.quantity_value,
            quantity_unit=self.quantity_unit,
            quantity_raw=self.quantity_raw,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, item: FridgeStockItem) -> FridgeStockItemEntity:
        return cls(
            id=item.id,
            ingredient_name=item.ingredient_name,
            quantity_value=item.quantity_value,
            quantity_unit=item.quantity_unit,
            quantity_raw=item.quantity_raw,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
