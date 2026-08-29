from collections.abc import Iterator
from typing import Literal

from app.dictation_streaming_service import stream_dictation
from app.domain.fridge_stock import FridgeStockItem
from app.persistence.repositories.fridge_stock_repository import FridgeStockRepository
from app.services.exceptions import NotFoundError


class FridgeStockService:
    """The persistent fridge inventory — plain CRUD, `deduct()` (called
    once a meal plan completes, see `SuggestionService`), and voice
    dictation (`parse_dictation_stream()` + `upsert_dictated_items()`, see
    the project plan)."""

    def __init__(self, repository: FridgeStockRepository) -> None:
        self._repository = repository

    def list_items(self) -> list[FridgeStockItem]:
        return self._repository.list_all()

    def add_item(self, item: FridgeStockItem) -> FridgeStockItem:
        return self._repository.add(item)

    def update_item(self, item_id: int, item: FridgeStockItem) -> FridgeStockItem:
        updated = self._repository.update(
            item_id,
            ingredient_name=item.ingredient_name,
            quantity_value=item.quantity_value,
            quantity_unit=item.quantity_unit,
            quantity_raw=item.quantity_raw,
        )
        if updated is None:
            raise NotFoundError(f"Fridge stock item {item_id} does not exist.")
        return updated

    def remove_item(self, item_id: int) -> None:
        if not self._repository.delete(item_id):
            raise NotFoundError(f"Fridge stock item {item_id} does not exist.")

    def deduct(self, stock_item_ids: list[int]) -> list[FridgeStockItem]:
        """Called once a meal plan completes (see `SuggestionService`) for
        the stock item IDs the recipe(s) reported using (deterministically
        sanitized beforehand — see `agent/stock_reference_check.py`).
        Returns what was removed, so the caller can report it back to the
        frontend for the "put back" undo (see the project plan) — silently
        ignores any id that's already gone (e.g. removed by a concurrent
        request) rather than raising.
        """
        removed = self._repository.get_many(stock_item_ids)
        self._repository.delete_many(stock_item_ids)
        return removed

    def parse_dictation_stream(
        self, audio_base64: str, audio_format: Literal["wav", "mp3"]
    ) -> Iterator[dict[str, object]]:
        """Streams the transcribe-then-structure pipeline for a dictated
        audio clip (see `VoiceDictation`, frontend) as SSE-ready event
        dicts (see `app/dictation_streaming_service.py` for the exact
        event shapes) — nothing is persisted until the user reviews the
        final `items` event and confirms via `upsert_dictated_items()`
        (`POST /api/fridge-stock/bulk`).

        Both pipeline stages (transcription, structuring) are local
        services now (see `agent/stt_client.py`, `agent/nlp_client.py`) —
        unlike meal suggestions, dictation needs no OpenRouter token or
        model, so there's no configuration to validate before starting.
        """
        return stream_dictation(audio_base64=audio_base64, audio_format=audio_format)

    def upsert_dictated_items(self, items: list[FridgeStockItem]) -> list[FridgeStockItem]:
        """For each item, updates the existing stock row of the same name
        (case-insensitive — re-dictating "milk, one liter" restates the
        current amount rather than piling up a duplicate) or adds a new
        one."""
        result: list[FridgeStockItem] = []
        for item in items:
            existing = self._repository.find_by_name(item.ingredient_name)
            if existing is not None:
                assert existing.id is not None
                updated = self._repository.update(
                    existing.id,
                    ingredient_name=item.ingredient_name,
                    quantity_value=item.quantity_value,
                    quantity_unit=item.quantity_unit,
                    quantity_raw=item.quantity_raw,
                )
                assert updated is not None
                result.append(updated)
            else:
                result.append(self._repository.add(item))
        return result
