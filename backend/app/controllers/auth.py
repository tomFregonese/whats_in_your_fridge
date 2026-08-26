from fastapi import APIRouter, Depends

from app.dependencies import get_security_service
from app.dto.auth_dto import AuthStatusDtoOut, SetTokenDtoIn, SetupPasswordDtoIn, UnlockDtoIn
from app.security.service import SecurityService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/status")
def get_auth_status(
    service: SecurityService = Depends(get_security_service),
) -> AuthStatusDtoOut:
    return AuthStatusDtoOut(
        password_set=service.is_password_set(),
        unlocked=service.is_unlocked(),
    )


@router.post("/setup", status_code=204)
def setup_password(
    dto: SetupPasswordDtoIn,
    service: SecurityService = Depends(get_security_service),
) -> None:
    service.setup_password(dto.password)


@router.post("/unlock", status_code=204)
def unlock(
    dto: UnlockDtoIn,
    service: SecurityService = Depends(get_security_service),
) -> None:
    service.unlock(dto.password)


@router.post("/lock", status_code=204)
def lock(service: SecurityService = Depends(get_security_service)) -> None:
    service.lock()


@router.post("/token", status_code=204)
def set_token(
    dto: SetTokenDtoIn,
    service: SecurityService = Depends(get_security_service),
) -> None:
    """Separate from `PATCH /api/settings` on purpose: the token belongs to
    the vault, not to `settings`, and must be settable during the
    "openrouter" onboarding step — before `settings` exists at all.
    """
    service.set_token(dto.token)
