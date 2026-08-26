from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.controllers import health

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

app.include_router(health.router, prefix="/api")
