import itertools
from collections.abc import Iterator
from typing import Literal

from app.agent import duplicate_check
from app.dictation_streaming_service import stream_dictation
from app.domain.fridge_stock import FridgeStockItem
from app.domain.merge_suggestion import MergeSuggestion
from app.persistence.repositories.fridge_stock_repository import FridgeStockRepository
from app.persistence.repositories.merge_dismissal_repository import MergeDismissalRepository
from app.services.exceptions import NotFoundError


class FridgeStockService:
    """The persistent fridge inventory — plain CRUD, `deduct()` (called
    once a meal plan completes, see `SuggestionService`), voice dictation
    (`parse_dictation_stream()` + `upsert_dictated_items()`, see the
    project plan), and duplicate-merge suggestions (`find_merge_suggestions()`
    + `merge_items()` + `dismiss_merge_suggestion()`, see
    `agent/duplicate_check.py`)."""

    def __init__(
        self,
        repository: FridgeStockRepository,
        dismissal_repository: MergeDismissalRepository,
    ) -> None:
        self._repository = repository
        self._dismissal_repository = dismissal_repository

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

    def find_merge_suggestions(self) -> list[MergeSuggestion]:
        """Asks the local model (see `agent/duplicate_check.py`) whether
        any two current ingredient names look like the same real
        ingredient — translation, typo, singular/plural — then resolves
        its (name-only) answer back to real stock rows and drops anything
        the user already dismissed. Recomputed on every call, nothing
        here is persisted (only a dismissal is, see
        `dismiss_merge_suggestion()`)."""
        items = self._repository.list_all()
        if len(items) < 2:
            return []

        names = [item.ingredient_name for item in items]
        groups = duplicate_check.find_duplicate_groups(ingredient_names=names)

        by_name = {item.ingredient_name: item for item in items}
        by_name_lower = {item.ingredient_name.strip().lower(): item for item in items}

        def resolve(name: str) -> FridgeStockItem | None:
            # Exact match first; a lowercase fallback covers a model that
            # alters case despite being told to copy names verbatim — a
            # name that still doesn't resolve is silently dropped, same
            # "don't fully trust the model's string fidelity" stance as
            # `agent/quantity_sanity_check.py`.
            return by_name.get(name) or by_name_lower.get(name.strip().lower())

        suggestions: list[MergeSuggestion] = []
        seen_pairs: set[tuple[str, str]] = set()
        for group in groups:
            resolved = {name: resolve(name) for name in group.names}
            valid_names = sorted({name for name, item in resolved.items() if item is not None})
            for name_a, name_b in itertools.combinations(valid_names, 2):
                pair_key = tuple(sorted((name_a.lower(), name_b.lower())))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)
                if self._dismissal_repository.is_dismissed(name_a, name_b):
                    continue
                suggested_name = (
                    group.suggested_name if group.suggested_name in valid_names else name_a
                )
                item_a = resolved[name_a]
                item_b = resolved[name_b]
                assert item_a is not None and item_b is not None
                suggestions.append(
                    MergeSuggestion(item_a=item_a, item_b=item_b, suggested_name=suggested_name)
                )
        return suggestions

    def merge_items(self, *, keep_id: int, remove_id: int, merged_name: str) -> FridgeStockItem:
        """Combines two stock rows into the one at `keep_id`, then deletes
        `remove_id`. Quantities are only summed when both rows agree on
        `quantity_unit` (including both `None`, i.e. two bare counts) and
        both have a numeric value — anything else (different units, a
        vague/null amount on either side) is too ambiguous to combine
        automatically, so `keep_id`'s own quantity is left untouched and
        the user can adjust it by hand afterward."""
        keep = self._repository.get(keep_id)
        remove = self._repository.get(remove_id)
        if keep is None or remove is None:
            raise NotFoundError("One of the fridge stock items to merge no longer exists.")

        same_unit = keep.quantity_unit == remove.quantity_unit
        both_have_values = keep.quantity_value is not None and remove.quantity_value is not None
        if same_unit and both_have_values:
            assert keep.quantity_value is not None and remove.quantity_value is not None
            quantity_value: float | None = keep.quantity_value + remove.quantity_value
            quantity_unit = keep.quantity_unit
            quantity_raw = None
        else:
            quantity_value = keep.quantity_value
            quantity_unit = keep.quantity_unit
            quantity_raw = keep.quantity_raw

        merged = self._repository.update(
            keep_id,
            ingredient_name=merged_name.strip(),
            quantity_value=quantity_value,
            quantity_unit=quantity_unit,
            quantity_raw=quantity_raw,
        )
        assert merged is not None
        self._repository.delete(remove_id)
        return merged

    def dismiss_merge_suggestion(self, name_a: str, name_b: str) -> None:
        self._dismissal_repository.dismiss(name_a, name_b)
