from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.controllers import allergies, health, onboarding, preferences, settings
from app.services.exceptions import AlreadyOnboardedError, NotFoundError, NotOnboardedError

app = FastAPI(title="What's in your fridge? API")

# Localhost-only deployment: the frontend's nginx proxy is the sole entry
# point (see docker-compose.yml, bound to 127.0.0.1), so a permissive CORS
# policy here does not widen the app's actual exposure.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# One handler per service-layer exception (see `app.services.exceptions`) —
# controllers never need a try/except of their own for these.
@app.exception_handler(NotFoundError)
async def handle_not_found(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(AlreadyOnboardedError)
async def handle_already_onboarded(request: Request, exc: AlreadyOnboardedError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(NotOnboardedError)
async def handle_not_onboarded(request: Request, exc: NotOnboardedError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


app.include_router(health.router, prefix="/api")
app.include_router(onboarding.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(allergies.router, prefix="/api")
app.include_router(preferences.router, prefix="/api")
