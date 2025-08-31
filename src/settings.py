import os
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


def get_env_file():
    """Determine which env file to use based on ENVIRONMENT variable."""
    env = os.getenv("ENVIRONMENT", "dev")
    env_files = {
        "dev": ".env.dev",
        "staging": ".env.staging",
        "prod": ".env.prod",
        "test": ".env.test"
    }
    return env_files.get(env, ".env.dev")

class Settings(BaseSettings):
    ENVIRONMENT: Literal["dev", "staging", "prod", "test"] = "dev"
    DATABASE_URL: str
    VALKEY_URL: str

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Replace postgres hostname with localhost when not in Docker
        if os.getenv("DOCKER_ENV") != "true":
            # Only replace the hostname part, not the protocol
            self.DATABASE_URL = self.DATABASE_URL.replace("@postgres:", "@localhost:")
            self.VALKEY_URL = self.VALKEY_URL.replace("valkey:", "localhost:")

    model_config = SettingsConfigDict(
        env_file=get_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()
