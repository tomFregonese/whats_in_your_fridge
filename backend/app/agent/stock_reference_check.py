"""Deterministic, code-level guard on which fridge stock item IDs a dish
claims to have used — same stance as `agent/allergy_check.py`: which
ingredients a dish actually uses is reported by the LLM, but which of
*our own* known stock IDs that's allowed to reference is never left to the
model alone. Defends against a hallucinated or stale ID reaching
`FridgeStockService.deduct()` and trying to remove a row that was never
offered (or no longer exists).
"""

from collections.abc import Set as AbstractSet

from app.agent.output_schema import PlatArgs


def sanitize_stock_ids(plats: list[PlatArgs], known_ids: AbstractSet[int]) -> None:
    """Mutates each `plat.ingredients_stock_ids` in place, dropping any ID
    not in `known_ids` (the fridge stock item IDs actually offered to the
    model for this run — see `FridgeInput.items`)."""
    for plat in plats:
        plat.ingredients_stock_ids = [
            stock_id for stock_id in plat.ingredients_stock_ids if stock_id in known_ids
        ]
