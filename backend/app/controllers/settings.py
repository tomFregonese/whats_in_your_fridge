from fastapi import APIRouter, Depends

from app.agent import client as agent_client
from app.agent.catalog import is_model_available, list_free_models
from app.dependencies import get_security_service, get_settings_service
from app.dto.model_dto import (
    FreeModelDtoOut,
    ModelStatusDtoOut,
    TestConnectionDtoIn,
    TestConnectionDtoOut,
)
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


@router.get("/model-status")
def get_model_status(
    settings_service: SettingsService = Depends(get_settings_service),
) -> ModelStatusDtoOut:
    model_id = settings_service.get_settings().openrouter_model_id
    available = model_id is not None and is_model_available(model_id)
    return ModelStatusDtoOut(model_id=model_id, available=available)


@router.post("/test-connection")
def test_connection(
    dto: TestConnectionDtoIn,
    security_service: SecurityService = Depends(get_security_service),
) -> TestConnectionDtoOut:
    """Sends a minimal request to OpenRouter to verify the stored token
    works with the given model. Returns ``ok: true`` on success, or
    ``ok: false`` with a detail message on failure.
    """
    try:
        token = security_service.get_token()
        ok = agent_client.test_connection(token=token, model=dto.model_id)
        detail = None if ok else "OpenRouter rejected the request."
        return TestConnectionDtoOut(ok=ok, detail=detail)
    except Exception as exc:
        return TestConnectionDtoOut(ok=False, detail=str(exc))
