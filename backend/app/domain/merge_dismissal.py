from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class MergeDismissal:
    """A user's "these are not the same ingredient" verdict on a pair of
    ingredient *names* — not stock-item ids. An id can be deleted and the
    same typo re-dictated later under a fresh id; the dismissal must still
    apply, so it's keyed by name, not id. `name_a`/`name_b` are always
    normalized (lowercased, trimmed) and stored in sorted order, so lookup
    is order-independent (see `persistence.repositories.
    merge_dismissal_repository.MergeDismissalRepository`)."""

    id: int | None
    name_a: str
    name_b: str
    created_at: datetime
