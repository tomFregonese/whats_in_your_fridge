from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.settings import Settings


class SettingsDtoIn(BaseModel):
    """PATCH payload — merges onto the currently persisted `Settings`.
    `openrouter_model_id` is optional: omit it to leave the current
    selection unchanged (used when only changing portions).

    The OpenRouter token itself does NOT go through this Dto — see
    `POST /api/auth/token` — it lives in the `vault` table, not `settings`,
    and setting it must work even before `settings` exists (see the
    "openrouter" onboarding step, which runs before the step that creates
    this row).
    """

    default_servings: int = Field(gt=0)
    openrouter_model_id: str | None = None

    def to_domain(self, current: Settings) -> Settings:
        return Settings(
            id=current.id,
            default_servings=self.default_servings,
            openrouter_model_id=(
                self.openrouter_model_id
                if self.openrouter_model_id is not None
                else current.openrouter_model_id
            ),
            created_at=current.created_at,
            updated_at=current.updated_at,
        )


class SettingsDtoOut(BaseModel):
    default_servings: int
    openrouter_model_id: str | None
    # Sourced from `security.has_token()`, not the `Settings` BO — a Dto
    # can aggregate more than one BO, same as `SuggestionDtoOut` will later
    # include `feedback` (see the project plan).
    openrouter_token_configured: bool

    @classmethod
    def from_domain(cls, settings: Settings, *, token_configured: bool) -> SettingsDtoOut:
        return cls(
            default_servings=settings.default_servings,
            openrouter_model_id=settings.openrouter_model_id,
            openrouter_token_configured=token_configured,
        )
