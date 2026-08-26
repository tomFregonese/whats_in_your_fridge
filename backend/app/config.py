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


settings = Settings()
