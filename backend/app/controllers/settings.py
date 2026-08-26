from fastapi import APIRouter, Depends

from app.dependencies import get_settings_service
from app.dto.settings_dto import SettingsDtoIn, SettingsDtoOut
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
def get_settings(service: SettingsService = Depends(get_settings_service)) -> SettingsDtoOut:
    return SettingsDtoOut.from_domain(service.get_settings())


@router.patch("")
def update_settings(
    dto: SettingsDtoIn,
    service: SettingsService = Depends(get_settings_service),
) -> SettingsDtoOut:
    current = service.get_settings()
    updated = service.save_settings(dto.to_domain(current))
    return SettingsDtoOut.from_domain(updated)
