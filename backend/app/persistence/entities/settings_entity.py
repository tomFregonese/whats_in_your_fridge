from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel

from app.domain.settings import Settings

DEFAULT_SERVINGS = 4


class SettingsEntity(SQLModel, table=True):
    """Singleton row (id=1). See `app.domain.settings.Settings` for the BO."""

    __tablename__ = "settings"

    id: int | None = Field(default=None, primary_key=True)
    default_servings: int = DEFAULT_SERVINGS
    openrouter_model_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    freezer_capacity_slots: int | None = None

    def to_domain(self) -> Settings:
        return Settings(
            id=self.id,
            default_servings=self.default_servings,
            openrouter_model_id=self.openrouter_model_id,
            created_at=self.created_at,
            updated_at=self.updated_at,
            freezer_capacity_slots=self.freezer_capacity_slots,
        )

    @classmethod
    def from_domain(cls, settings: Settings) -> SettingsEntity:
        return cls(
            id=settings.id,
            default_servings=settings.default_servings,
            openrouter_model_id=settings.openrouter_model_id,
            created_at=settings.created_at,
            updated_at=settings.updated_at,
            freezer_capacity_slots=settings.freezer_capacity_slots,
        )
