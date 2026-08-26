"""FastAPI dependency-injection providers.

Centralizes how each layer is wired to the next (repository -> service) so
controllers only ever declare ``Depends(get_xxx_service)`` — never
construct a repository or service themselves.
"""

from fastapi import Depends
from sqlmodel import Session

from app.db import get_session
from app.persistence.repositories.allergy_repository import AllergyRepository
from app.persistence.repositories.fridge_input_repository import FridgeInputRepository
from app.persistence.repositories.preference_note_repository import PreferenceNoteRepository
from app.persistence.repositories.settings_repository import SettingsRepository
from app.security.service import SecurityService
from app.services.allergy_service import AllergyService
from app.services.onboarding_service import OnboardingService
from app.services.preference_service import PreferenceService
from app.services.settings_service import SettingsService
from app.services.suggestion_service import SuggestionService


def get_settings_repository(session: Session = Depends(get_session)) -> SettingsRepository:
    return SettingsRepository(session)


def get_allergy_repository(session: Session = Depends(get_session)) -> AllergyRepository:
    return AllergyRepository(session)


def get_preference_repository(
    session: Session = Depends(get_session),
) -> PreferenceNoteRepository:
    return PreferenceNoteRepository(session)


def get_settings_service(
    repository: SettingsRepository = Depends(get_settings_repository),
) -> SettingsService:
    return SettingsService(repository)


def get_allergy_service(
    repository: AllergyRepository = Depends(get_allergy_repository),
) -> AllergyService:
    return AllergyService(repository)


def get_preference_service(
    repository: PreferenceNoteRepository = Depends(get_preference_repository),
) -> PreferenceService:
    return PreferenceService(repository)


def get_onboarding_service(
    settings_repository: SettingsRepository = Depends(get_settings_repository),
    allergy_repository: AllergyRepository = Depends(get_allergy_repository),
    preference_repository: PreferenceNoteRepository = Depends(get_preference_repository),
) -> OnboardingService:
    return OnboardingService(settings_repository, allergy_repository, preference_repository)


def get_security_service(session: Session = Depends(get_session)) -> SecurityService:
    return SecurityService(session)


def get_fridge_input_repository(
    session: Session = Depends(get_session),
) -> FridgeInputRepository:
    return FridgeInputRepository(session)


def get_suggestion_service(
    repository: FridgeInputRepository = Depends(get_fridge_input_repository),
) -> SuggestionService:
    return SuggestionService(repository)
