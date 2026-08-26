from fastapi import APIRouter, Depends

from app.dependencies import get_security_service
from app.dto.auth_dto import AuthStatusDtoOut, SetupPasswordDtoIn, UnlockDtoIn
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
