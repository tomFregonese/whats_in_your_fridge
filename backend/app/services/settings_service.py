from app.domain.settings import Settings
from app.persistence.repositories.settings_repository import SettingsRepository
from app.services.exceptions import NotOnboardedError


class SettingsService:
    def __init__(self, repository: SettingsRepository) -> None:
        self._repository = repository

    def get_settings(self) -> Settings:
        settings = self._repository.get()
        if settings is None:
            raise NotOnboardedError(
                "Settings have not been configured yet — complete onboarding first."
            )
        return settings

    def save_settings(self, settings: Settings) -> Settings:
        return self._repository.save(settings)
