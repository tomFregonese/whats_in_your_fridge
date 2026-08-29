from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.domain.fridge_stock import FridgeStockItem
from app.domain.merge_suggestion import MergeSuggestion


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


class MergeSuggestionDtoOut(BaseModel):
    """Body of one entry in `GET /api/fridge-stock/merge-suggestions` — two
    existing stock rows the local model judged to name the same real
    ingredient (see `agent/duplicate_check.py`), plus the name it'd
    suggest keeping."""

    item_a: FridgeStockItemDtoOut
    item_b: FridgeStockItemDtoOut
    suggested_name: str

    @classmethod
    def from_domain(cls, suggestion: MergeSuggestion) -> MergeSuggestionDtoOut:
        return cls(
            item_a=FridgeStockItemDtoOut.from_domain(suggestion.item_a),
            item_b=FridgeStockItemDtoOut.from_domain(suggestion.item_b),
            suggested_name=suggestion.suggested_name,
        )


class FridgeStockMergeDtoIn(BaseModel):
    """Body of `POST /api/fridge-stock/merge` — the user's one-click
    confirmation of a `MergeSuggestionDtoOut`. `merged_name` is passed
    explicitly (rather than re-derived server-side) since the frontend
    already has the model's `suggested_name` and there's no second
    "pick a name" step."""

    keep_item_id: int
    remove_item_id: int
    merged_name: str = Field(min_length=1)

    @model_validator(mode="after")
    def _ids_must_differ(self) -> FridgeStockMergeDtoIn:
        if self.keep_item_id == self.remove_item_id:
            raise ValueError("keep_item_id and remove_item_id must be different.")
        return self


class MergeDismissalDtoIn(BaseModel):
    """Body of `POST /api/fridge-stock/merge-suggestions/dismiss` — a
    name pair the user says are NOT the same ingredient, so it's never
    suggested again (see `MergeDismissalRepository`)."""

    name_a: str = Field(min_length=1)
    name_b: str = Field(min_length=1)
