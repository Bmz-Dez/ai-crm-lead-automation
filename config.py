from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    groq_api_key: str = "dummy_key_for_ci"
    groq_model: str = "openai/gpt-oss-120b"
    hubspot_api_key: str = ""
    crm_dry_run: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()