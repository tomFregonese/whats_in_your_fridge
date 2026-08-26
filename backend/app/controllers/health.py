from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def get_health() -> dict[str, str]:
    """Liveness check used by the Docker healthcheck and the frontend proxy."""
    return {"status": "ok"}
