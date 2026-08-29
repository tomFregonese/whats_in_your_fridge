from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.domain.fridge_stock import FridgeStockItem


class FridgeStockItemDtoIn(BaseModel):
    """Used both for `POST` (create) and `PATCH` (full replace of the
    editable fields — the UI always submits the whole edited row, so there's
    no need for a separate partial-update Dto)."""

    ingredient_name: str = Field(min_length=1)
    quantity_value: float | None = None
    quantity_unit: str | None = None
    quantity_raw: str | None = None

    def to_domain(self) -> FridgeStockItem:
        now = datetime.now(UTC)
        return FridgeStockItem(
            id=None,
            ingredient_name=self.ingredient_name.strip(),
            quantity_value=self.quantity_value,
            quantity_unit=self.quantity_unit,
            quantity_raw=self.quantity_raw,
            created_at=now,
            updated_at=now,
        )


class FridgeStockItemDtoOut(BaseModel):
    id: int
    ingredient_name: str
    quantity_value: float | None
    quantity_unit: str | None
    quantity_raw: str | None
    updated_at: datetime

    @classmethod
    def from_domain(cls, item: FridgeStockItem) -> FridgeStockItemDtoOut:
        assert item.id is not None, "FridgeStockItemDtoOut requires a persisted FridgeStockItem"
        return cls(
            id=item.id,
            ingredient_name=item.ingredient_name,
            quantity_value=item.quantity_value,
            quantity_unit=item.quantity_unit,
            quantity_raw=item.quantity_raw,
            updated_at=item.updated_at,
        )


class DictationParseDtoIn(BaseModel):
    """Body of `POST /api/fridge-stock/dictation` — a raw audio clip
    recorded in the browser (see `VoiceDictation`, frontend). The response
    is an SSE stream, not a Dto (see `app/dictation_streaming_service.py`
    for the event shapes, plain dicts by the same convention
    `streaming_service.py` already uses for its own SSE events)."""

    audio_base64: str = Field(min_length=1)
    audio_format: Literal["wav", "mp3"]


class FridgeStockBulkAddDtoIn(BaseModel):
    """Body of `POST /api/fridge-stock/bulk` — the reviewed/edited items
    from a dictation pass, committed via `FridgeStockService.upsert_dictated_items`
    (updates a same-name existing row instead of duplicating it)."""

    items: list[FridgeStockItemDtoIn] = Field(min_length=1)
