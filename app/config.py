"""All settings come from environment variables / .env - never hardcoded."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Safety guard: stop the agent loop after this many tool rounds.
    max_tool_iterations: int = 5

    database_path: str = "app.db"

    admin_username: str = "admin"
    admin_password: str = "admin123"

    log_level: str = "INFO"


settings = Settings()
