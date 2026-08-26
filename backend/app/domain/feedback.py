from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Feedback:
    """Post-meal feedback for one suggestion — at most one per suggestion."""

    id: int | None
    suggestion_id: int
    liked: bool | None
    comment: str | None
