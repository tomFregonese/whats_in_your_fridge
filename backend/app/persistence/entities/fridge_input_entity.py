from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel

from app.domain.fridge_input import FridgeInput, FridgeInputItem, FridgeInputMode, SourcingMode


class FridgeInputEntity(SQLModel, table=True):
    __tablename__ = "fridge_input"

    id: int | None = Field(default=None, primary_key=True)
    mode: str
    sourcing_mode: str = SourcingMode.FRIDGE_PLUS_SHOPPING.value
    free_text: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    days: int | None = None

    def to_domain(self) -> FridgeInput:
        """Maps this row only — `items` stays empty here, populated by the
        repository instead. See `FridgeInput`'s docstring.
        """
        return FridgeInput(
            id=self.id,
            mode=FridgeInputMode(self.mode),
            sourcing_mode=SourcingMode(self.sourcing_mode),
            free_text=self.free_text,
            created_at=self.created_at,
            days=self.days,
        )

    @classmethod
    def from_domain(cls, fridge_input: FridgeInput) -> FridgeInputEntity:
        return cls(
            id=fridge_input.id,
            mode=fridge_input.mode.value,
            sourcing_mode=fridge_input.sourcing_mode.value,
            free_text=fridge_input.free_text,
            created_at=fridge_input.created_at,
            days=fridge_input.days,
        )


class FridgeInputItemEntity(SQLModel, table=True):
    __tablename__ = "fridge_input_item"

    id: int | None = Field(default=None, primary_key=True)
    fridge_input_id: int = Field(foreign_key="fridge_input.id", index=True)
    ingredient_name: str
    quantity_value: float | None = None
    quantity_unit: str | None = None
    quantity_raw: str | None = None
    fridge_stock_item_id: int | None = Field(
        default=None, foreign_key="fridge_stock_item.id", index=True
    )

    def to_domain(self) -> FridgeInputItem:
        return FridgeInputItem(
            id=self.id,
            fridge_input_id=self.fridge_input_id,
            ingredient_name=self.ingredient_name,
            quantity_value=self.quantity_value,
            quantity_unit=self.quantity_unit,
            quantity_raw=self.quantity_raw,
            fridge_stock_item_id=self.fridge_stock_item_id,
        )

    @classmethod
    def from_domain(cls, item: FridgeInputItem) -> FridgeInputItemEntity:
        if item.fridge_input_id is None:
            raise ValueError("FridgeInputItem.fridge_input_id must be set before persisting")
        return cls(
            id=item.id,
            fridge_input_id=item.fridge_input_id,
            ingredient_name=item.ingredient_name,
            quantity_value=item.quantity_value,
            quantity_unit=item.quantity_unit,
            quantity_raw=item.quantity_raw,
            fridge_stock_item_id=item.fridge_stock_item_id,
        )
