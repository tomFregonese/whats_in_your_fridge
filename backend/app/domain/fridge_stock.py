from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class FridgeStockItem:
    """One ingredient permanently tracked in the household's fridge —
    unlike `FridgeInputItem` (a per-generation submission snapshot, see
    `app.domain.fridge_input`), this survives across sessions until edited,
    deleted, or automatically deducted once a recipe reports using it (see
    `app.services.fridge_stock_service.FridgeStockService.deduct`).
    """

    id: int | None
    ingredient_name: str
    quantity_value: float | None
    quantity_unit: str | None
    quantity_raw: str | None
    created_at: datetime
    updated_at: datetime
