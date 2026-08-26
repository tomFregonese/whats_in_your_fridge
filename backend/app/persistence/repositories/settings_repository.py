from datetime import UTC, datetime

from sqlmodel import Session

from app.domain.settings import Settings
from app.persistence.entities.settings_entity import SettingsEntity

SINGLETON_ID = 1


class SettingsRepository:
    """Reads/writes the singleton `settings` row (id=1)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self) -> Settings | None:
        entity = self._session.get(SettingsEntity, SINGLETON_ID)
        return entity.to_domain() if entity is not None else None

    def save(self, settings: Settings) -> Settings:
        """Creates the singleton row if it doesn't exist yet, else updates
        it in place. `created_at` is preserved across updates and
        `updated_at` is always bumped to now — callers never manage either.
        """
        existing = self._session.get(SettingsEntity, SINGLETON_ID)
        now = datetime.now(UTC)

        if existing is None:
            entity = SettingsEntity.from_domain(settings)
            entity.id = SINGLETON_ID
            entity.created_at = now
            entity.updated_at = now
            self._session.add(entity)
        else:
            existing.default_servings = settings.default_servings
            existing.openrouter_model_id = settings.openrouter_model_id
            existing.updated_at = now
            entity = existing

        self._session.commit()
        self._session.refresh(entity)
        return entity.to_domain()
