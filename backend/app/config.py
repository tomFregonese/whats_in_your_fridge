from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-level *technical* settings, sourced from environment
    variables.

    Only non-sensitive, infra-level values belong here. Everything the user
    needs to configure or provide (OpenRouter token, chosen model, allergies,
    portions, ...) lives in the database instead and is managed entirely
    through the UI — see ``security/`` and ``persistence/``.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    db_path: str = "/data/fridge.db"
    history_window_n: int = 10
    # Internal-only Docker Compose service name (see `docker-compose.yml`'s
    # `stt` service) — never reachable from outside the Docker network.
    stt_url: str = "http://stt:8001"
    # Same, for the local dictation-structuring service (see
    # `docker-compose.yml`'s `nlp` service).
    nlp_url: str = "http://nlp:8002"
    # Baked into the image at build time (see backend/Dockerfile's
    # ARG/ENV) — "dev" here only means running outside a built image, e.g.
    # local `uvicorn` during development or in tests.
    app_version: str = "dev"


settings = Settings()
