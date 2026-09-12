import itertools
import re
from collections.abc import Iterator
from typing import Literal

from app.agent import duplicate_check
from app.agent.text_normalize import normalize
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
                lower_a, lower_b = name_a.lower(), name_b.lower()
                pair_key = (lower_a, lower_b) if lower_a <= lower_b else (lower_b, lower_a)
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
        `remove_id`. The two quantities are summed as numbers — converting
        between compatible units first (e.g. 500g + 1kg = 1.5kg), never
        guessing across incompatible ones (e.g. kg vs a bare count) —
        whenever both sides can be confidently read as a plain number (see
        `_sum_numeric_quantities`). That conversion/summing is plain
        deterministic code, not the local model: same "never trust the
        LLM with verifiable arithmetic" stance already used for every
        other quantity in this app (`agent/quantity_sanity_check.py`,
        `agent/conservation_sanity_check.py`) — and unlike duplicate-name
        detection (`agent/duplicate_check.py`), reading "1kg"/"6kg" and
        adding them up isn't a judgment call an LLM is actually needed
        for.

        Either side being too vague to read as a number (an incompatible
        unit, free text like "a bit", or nothing at all) falls back to
        combining both as text (`_combine_quantity_descriptions`) rather
        than keeping only `keep_id`'s and silently discarding
        `remove_id`'s entirely.

        The result always lands in `quantity_raw` — never
        `quantity_value`/`quantity_unit`, which `pages/Fridge.tsx` never
        reads or lets the user edit for a stock row (only voice dictation,
        a different flow, uses those two)."""
        keep = self._repository.get(keep_id)
        remove = self._repository.get(remove_id)
        if keep is None or remove is None:
            raise NotFoundError("One of the fridge stock items to merge no longer exists.")

        quantity_raw = _sum_numeric_quantities(keep, remove) or _combine_quantity_descriptions(
            keep, remove
        )

        merged = self._repository.update(
            keep_id,
            ingredient_name=merged_name.strip(),
            quantity_value=None,
            quantity_unit=None,
            quantity_raw=quantity_raw,
        )
        assert merged is not None
        self._repository.delete(remove_id)
        return merged

    def dismiss_merge_suggestion(self, name_a: str, name_b: str) -> None:
        self._dismissal_repository.dismiss(name_a, name_b)


# Normalized (see `agent/text_normalize.normalize` — case/accent-insensitive,
# same helper `allergy_check`/`equipment_check` use) unit token -> (dimension,
# factor to that dimension's base unit: grams for mass, millilitres for
# volume) — lets `_sum_numeric_quantities` convert between units of the same
# kind (500g + 1kg) rather than requiring an exact match.
_UNIT_FACTORS: dict[str, tuple[str, float]] = {
    "g": ("mass", 1),
    "gr": ("mass", 1),
    "gramme": ("mass", 1),
    "grammes": ("mass", 1),
    "gram": ("mass", 1),
    "grams": ("mass", 1),
    "kg": ("mass", 1000),
    "kilo": ("mass", 1000),
    "kilos": ("mass", 1000),
    "kilogramme": ("mass", 1000),
    "kilogrammes": ("mass", 1000),
    "kilogram": ("mass", 1000),
    "kilograms": ("mass", 1000),
    "mg": ("mass", 0.001),
    "ml": ("volume", 1),
    "millilitre": ("volume", 1),
    "millilitres": ("volume", 1),
    "cl": ("volume", 10),
    "centilitre": ("volume", 10),
    "centilitres": ("volume", 10),
    "l": ("volume", 1000),
    "litre": ("volume", 1000),
    "litres": ("volume", 1000),
    "liter": ("volume", 1000),
    "liters": ("volume", 1000),
}

# Matches a *plain* "NUMBER" or "NUMBER UNIT" quantity_raw, nothing else —
# deliberately conservative: "1kg", "500 g", "6" all match; "about 2kg",
# "1kg (frozen)", "a bit less than a kilo" don't, and fall back to
# `_combine_quantity_descriptions` rather than risk misreading free text.
_RAW_QUANTITY_RE = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*([a-zA-ZÀ-ÿ]*)\s*$")


def _parsed_amount(item: FridgeStockItem) -> tuple[float, str] | None:
    """(value, unit token) read with confidence from `item` — either
    already structured (`quantity_value`/`quantity_unit`, the dictation
    shape) or a `quantity_raw` that's cleanly "NUMBER" or "NUMBER UNIT"
    (see `_RAW_QUANTITY_RE`). `None` when neither is available or
    `quantity_raw` doesn't match that shape."""
    if item.quantity_value is not None:
        return item.quantity_value, item.quantity_unit or ""
    if item.quantity_raw:
        match = _RAW_QUANTITY_RE.match(item.quantity_raw)
        if match:
            value_str, unit_token = match.groups()
            return float(value_str.replace(",", ".")), unit_token
    return None


def _dimension(unit_token: str) -> tuple[str, float]:
    """The "kind" a unit belongs to (so two amounts of the same kind can
    be summed) plus its factor to that kind's base unit. A bare count
    (`unit_token` empty) is its own kind. An unrecognized unit (a custom
    "boîtes", "sachets", ...) still gets a kind of its own, keyed by its
    normalized spelling — two occurrences of the exact same unrecognized
    unit can still be summed together, just never converted to/from a
    different one this module doesn't know how to relate it to."""
    if not unit_token:
        return "count", 1.0
    normalized = normalize(unit_token)
    return _UNIT_FACTORS.get(normalized, (normalized, 1.0))


def _sum_numeric_quantities(keep: FridgeStockItem, remove: FridgeStockItem) -> str | None:
    """A human-readable total (e.g. "1.5 kg") when both quantities parse
    (see `_parsed_amount`) as the same kind of unit (see `_dimension`) —
    `None` when either side is too vague to read as a number, or the two
    units aren't the same kind (e.g. kg vs a bare count); `merge_items()`
    falls back to combining both as text in that case."""
    keep_amount = _parsed_amount(keep)
    remove_amount = _parsed_amount(remove)
    if keep_amount is None or remove_amount is None:
        return None

    keep_value, keep_unit = keep_amount
    remove_value, remove_unit = remove_amount
    keep_dimension, keep_factor = _dimension(keep_unit)
    remove_dimension, remove_factor = _dimension(remove_unit)
    if keep_dimension != remove_dimension:
        return None

    # Expressed in `keep`'s own unit/spelling — it's the row that
    # survives, and keeps the result consistent with whatever the
    # household is used to typing.
    total = keep_value + remove_value * remove_factor / keep_factor
    return f"{total:g} {keep_unit}".strip()


def _describe_quantity(item: FridgeStockItem) -> str | None:
    """Human-readable amount for one side of a merge that can't be summed
    as a clean number — prefers the free-text `quantity_raw` a manually
    typed item actually has; falls back to formatting `quantity_value`/
    `quantity_unit` for a dictated one. `None` when the item carries no
    quantity information at all."""
    if item.quantity_raw:
        return item.quantity_raw
    if item.quantity_value is not None:
        unit = f" {item.quantity_unit}" if item.quantity_unit else ""
        return f"{item.quantity_value:g}{unit}"
    return None


def _combine_quantity_descriptions(keep: FridgeStockItem, remove: FridgeStockItem) -> str | None:
    """Used by `merge_items()` whenever the two quantities can't be summed
    into one number — joins both sides' amounts into `quantity_raw` so
    neither is silently lost, rather than keeping only `keep`'s."""
    keep_desc = _describe_quantity(keep)
    remove_desc = _describe_quantity(remove)
    if keep_desc and remove_desc and keep_desc != remove_desc:
        return f"{keep_desc} + {remove_desc}"
    return keep_desc or remove_desc
