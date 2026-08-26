from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from app.domain.allergy import Allergy
from app.domain.preference_note import PreferenceNote, PreferenceSource
from app.domain.settings import Settings


class OnboardingDtoIn(BaseModel):
    """Cold-start payload — spans three BOs (`Settings`, `Allergy`,
    `PreferenceNote`), so unlike other Dtos here it has no single
    `to_domain()`. Mapping still lives on the Dto itself, just split into
    one method per target BO.
    """

    default_servings: int = Field(gt=0)
    allergies: list[str] = Field(default_factory=list)
    preference_notes: list[str] = Field(default_factory=list)

    def to_settings(self) -> Settings:
        now = datetime.now(UTC)
        return Settings(
            id=None,
            default_servings=self.default_servings,
            openrouter_model_id=None,
            created_at=now,
            updated_at=now,
        )

    def to_allergies(self) -> list[Allergy]:
        return [
            Allergy(id=None, ingredient_name=name.strip(), notes=None)
            for name in self.allergies
            if name.strip()
        ]

    def to_preference_notes(self) -> list[PreferenceNote]:
        now = datetime.now(UTC)
        return [
            PreferenceNote(
                id=None, content=content.strip(), source=PreferenceSource.ONBOARDING, created_at=now
            )
            for content in self.preference_notes
            if content.strip()
        ]


class OnboardingStatusDtoOut(BaseModel):
    onboarded: bool
