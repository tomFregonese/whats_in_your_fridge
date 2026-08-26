from fastapi import APIRouter, Depends

from app.agent.catalog import list_free_models
from app.dependencies import get_security_service, get_settings_service
from app.dto.model_dto import FreeModelDtoOut
from app.dto.settings_dto import SettingsDtoIn, SettingsDtoOut
from app.security.service import SecurityService
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
def get_settings(
    settings_service: SettingsService = Depends(get_settings_service),
    security_service: SecurityService = Depends(get_security_service),
) -> SettingsDtoOut:
    return SettingsDtoOut.from_domain(
        settings_service.get_settings(), token_configured=security_service.has_token()
    )


@router.patch("")
def update_settings(
    dto: SettingsDtoIn,
    settings_service: SettingsService = Depends(get_settings_service),
    security_service: SecurityService = Depends(get_security_service),
) -> SettingsDtoOut:
    current = settings_service.get_settings()
    updated = settings_service.save_settings(dto.to_domain(current))
    return SettingsDtoOut.from_domain(updated, token_configured=security_service.has_token())


@router.get("/models")
def get_free_models() -> list[FreeModelDtoOut]:
    return [FreeModelDtoOut.from_domain(model) for model in list_free_models()]
