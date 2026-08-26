from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.settings import Settings


class SettingsDtoIn(BaseModel):
    """PATCH payload — merges onto the currently persisted `Settings`.

    `openrouter_model_id` isn't settable through this Dto yet: it gets its
    own flow once the live model picker lands (project plan, milestone 4).
    """

    default_servings: int = Field(gt=0)

    def to_domain(self, current: Settings) -> Settings:
        return Settings(
            id=current.id,
            default_servings=self.default_servings,
            openrouter_model_id=current.openrouter_model_id,
            created_at=current.created_at,
            updated_at=current.updated_at,
        )


class SettingsDtoOut(BaseModel):
    default_servings: int
    openrouter_model_id: str | None

    @classmethod
    def from_domain(cls, settings: Settings) -> SettingsDtoOut:
        return cls(
            default_servings=settings.default_servings,
            openrouter_model_id=settings.openrouter_model_id,
        )
