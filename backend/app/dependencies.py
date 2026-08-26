"""FastAPI dependency-injection providers.

Centralizes how each layer is wired to the next (repository -> service) so
controllers only ever declare ``Depends(get_xxx_service)`` — never
construct a repository or service themselves.
"""

from fastapi import Depends
from sqlmodel import Session

from app.agent.dedup import DedupProvider, RecentDishNamesDedupProvider
from app.config import settings as app_settings
from app.db import get_session
from app.persistence.repositories.agent_run_repository import AgentRunRepository
from app.persistence.repositories.allergy_repository import AllergyRepository
from app.persistence.repositories.feedback_repository import FeedbackRepository
from app.persistence.repositories.fridge_input_repository import FridgeInputRepository
from app.persistence.repositories.preference_note_repository import PreferenceNoteRepository
from app.persistence.repositories.settings_repository import SettingsRepository
from app.persistence.repositories.suggestion_repository import SuggestionRepository
from app.security.service import SecurityService
from app.services.allergy_service import AllergyService
from app.services.feedback_service import FeedbackService
from app.services.meal_plan_service import MealPlanService
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


def get_agent_run_repository(session: Session = Depends(get_session)) -> AgentRunRepository:
    return AgentRunRepository(session)


def get_suggestion_repository(session: Session = Depends(get_session)) -> SuggestionRepository:
    return SuggestionRepository(session)


def get_dedup_provider(
    repository: SuggestionRepository = Depends(get_suggestion_repository),
) -> DedupProvider:
    return RecentDishNamesDedupProvider(repository, app_settings.history_window_n)


def get_suggestion_service(
    fridge_input_repository: FridgeInputRepository = Depends(get_fridge_input_repository),
    agent_run_repository: AgentRunRepository = Depends(get_agent_run_repository),
    suggestion_repository: SuggestionRepository = Depends(get_suggestion_repository),
    allergy_repository: AllergyRepository = Depends(get_allergy_repository),
    preference_repository: PreferenceNoteRepository = Depends(get_preference_repository),
    settings_service: SettingsService = Depends(get_settings_service),
    security_service: SecurityService = Depends(get_security_service),
    dedup_provider: DedupProvider = Depends(get_dedup_provider),
) -> SuggestionService:
    return SuggestionService(
        fridge_input_repository,
        agent_run_repository,
        suggestion_repository,
        allergy_repository,
        preference_repository,
        settings_service,
        security_service,
        dedup_provider,
    )


def get_meal_plan_service(
    repository: SuggestionRepository = Depends(get_suggestion_repository),
) -> MealPlanService:
    return MealPlanService(repository)


def get_feedback_repository(session: Session = Depends(get_session)) -> FeedbackRepository:
    return FeedbackRepository(session)


def get_feedback_service(
    feedback_repository: FeedbackRepository = Depends(get_feedback_repository),
    suggestion_repository: SuggestionRepository = Depends(get_suggestion_repository),
    preference_repository: PreferenceNoteRepository = Depends(get_preference_repository),
) -> FeedbackService:
    return FeedbackService(feedback_repository, suggestion_repository, preference_repository)
