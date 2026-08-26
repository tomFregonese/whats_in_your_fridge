from fastapi import APIRouter, Depends

from app.dependencies import get_onboarding_service
from app.dto.onboarding_dto import OnboardingDtoIn, OnboardingStatusDtoOut
from app.dto.settings_dto import SettingsDtoOut
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
    service: OnboardingService = Depends(get_onboarding_service),
) -> SettingsDtoOut:
    settings = service.complete_onboarding(
        settings=dto.to_settings(),
        allergies=dto.to_allergies(),
        preference_notes=dto.to_preference_notes(),
    )
    return SettingsDtoOut.from_domain(settings)
