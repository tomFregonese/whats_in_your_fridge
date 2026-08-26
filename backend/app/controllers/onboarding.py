from fastapi import APIRouter, Depends

from app.dependencies import get_onboarding_service, get_security_service
from app.dto.onboarding_dto import OnboardingDtoIn, OnboardingStatusDtoOut
from app.dto.settings_dto import SettingsDtoOut
from app.security.service import SecurityService
from app.services.onboarding_service import OnboardingService

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.get("/status")
def get_onboarding_status(
    service: OnboardingService = Depends(get_onboarding_service),
) -> OnboardingStatusDtoOut:
    return OnboardingStatusDtoOut(onboarded=service.is_onboarded())


@router.post("", status_code=201)
def complete_onboarding(
    dto: OnboardingDtoIn,
    onboarding_service: OnboardingService = Depends(get_onboarding_service),
    security_service: SecurityService = Depends(get_security_service),
) -> SettingsDtoOut:
    settings = onboarding_service.complete_onboarding(
        settings=dto.to_settings(),
        allergies=dto.to_allergies(),
        preference_notes=dto.to_preference_notes(),
    )
    # The token (if any) was already set in the earlier "openrouter"
    # onboarding step via `POST /api/auth/token`, independently of this
    # call — reflect its real status rather than hardcoding False.
    return SettingsDtoOut.from_domain(settings, token_configured=security_service.has_token())
