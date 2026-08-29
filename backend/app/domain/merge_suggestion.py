from __future__ import annotations

from dataclasses import dataclass

from app.domain.fridge_stock import FridgeStockItem


@dataclass
class MergeSuggestion:
    """One pair of persistent fridge-stock items the local model judged to
    name the same real ingredient (see `agent/duplicate_check.py`) —
    recomputed on every check (`FridgeStockService.find_merge_suggestions`),
    never itself persisted. Only a *dismissal* of one survives across
    requests (see `domain.merge_dismissal.MergeDismissal`)."""

    item_a: FridgeStockItem
    item_b: FridgeStockItem
    suggested_name: str
