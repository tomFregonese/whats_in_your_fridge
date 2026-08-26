from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class PreferenceSource(StrEnum):
    """Where a soft preference note came from."""

    ONBOARDING = "onboarding"
    FEEDBACK = "feedback"
    MANUAL = "manual"


@dataclass
class PreferenceNote:
    """One raw soft-preference note (V1: no structured compaction — see
    the project plan, deferred to V2).
    """

    id: int | None
    content: str
    source: PreferenceSource
    created_at: datetime
