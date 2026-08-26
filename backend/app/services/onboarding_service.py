from app.domain.allergy import Allergy
from app.domain.preference_note import PreferenceNote
from app.domain.settings import Settings
from app.persistence.repositories.allergy_repository import AllergyRepository
from app.persistence.repositories.preference_note_repository import PreferenceNoteRepository
from app.persistence.repositories.settings_repository import SettingsRepository
from app.services.exceptions import AlreadyOnboardedError


class OnboardingService:
    """Orchestrates the cold-start flow: creates `settings` and seeds
    allergies/preferences in one action. Spans three aggregates, so unlike
    the other services here it isn't backed by a single repository.
    """

    def __init__(
        self,
        settings_repository: SettingsRepository,
        allergy_repository: AllergyRepository,
        preference_repository: PreferenceNoteRepository,
    ) -> None:
        self._settings_repository = settings_repository
        self._allergy_repository = allergy_repository
        self._preference_repository = preference_repository

    def is_onboarded(self) -> bool:
        return self._settings_repository.get() is not None

    def complete_onboarding(
        self,
        settings: Settings,
        allergies: list[Allergy],
        preference_notes: list[PreferenceNote],
    ) -> Settings:
        if self.is_onboarded():
            raise AlreadyOnboardedError("Onboarding has already been completed.")

        saved_settings = self._settings_repository.save(settings)

        for allergy in allergies:
            self._allergy_repository.add(allergy)
        for note in preference_notes:
            self._preference_repository.add(note)

        return saved_settings
