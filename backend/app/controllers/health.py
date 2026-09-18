from fastapi import APIRouter

from app.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def get_health() -> dict[str, str]:
    """Liveness check used by the Docker healthcheck and the frontend's
    update-check banner (see frontend's `api/health.ts`)."""
    return {"status": "ok", "version": settings.app_version}
