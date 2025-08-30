from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ENVIRONMENT: Literal["dev", "staging", "prod"] = "dev"
    DATABASE_URL: str
    VALKEY_URL: str

    # model_config = SettingsConfigDict(
    #     env_file=".env.dev",
    #     env_file_encoding="utf-8",
    #     extra="ignore",
    # )

    model_config = SettingsConfigDict(
        env_file=(
            ".env.dev" if ENVIRONMENT == "dev" else
            ".env.staging" if ENVIRONMENT == "staging" else
            ".env.prod"
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()
    