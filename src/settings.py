import os
from typing import Literal
from urllib.parse import urlparse, urlunparse

from pydantic_settings import BaseSettings, SettingsConfigDict


def get_env_file():
    """Determine which env file to use based on ENVIRONMENT variable."""
    env = os.getenv("ENVIRONMENT", "dev")
    env_files = {
        "dev": ".env.dev",
        "staging": ".env.staging",
        "prod": ".env.prod",
        "test": ".env.test",
    }
    return env_files.get(env, ".env.dev")


def rewrite_host(url: str, docker_host: str, new_host: str = "localhost") -> str:
    """Rewrite the host of a URL when it matches a docker service name.

    Only the host component is replaced; scheme, credentials, port, path, and
    query are preserved. Returns the URL unchanged if the host does not match.
    """
    parsed = urlparse(url)
    if parsed.hostname != docker_host:
        return url

    userinfo = ""
    if parsed.username is not None or parsed.password is not None:
        userinfo = parsed.username or ""
        if parsed.password is not None:
            userinfo += f":{parsed.password}"
        userinfo += "@"

    netloc = f"{userinfo}{new_host}"
    if parsed.port:
        netloc += f":{parsed.port}"

    return urlunparse(parsed._replace(netloc=netloc))


class Settings(BaseSettings):
    ENVIRONMENT: Literal["dev", "staging", "prod", "test"] = "dev"
    DATABASE_URL: str
    VALKEY_URL: str
    SECRET_KEY: str = "change-me-in-production"  # Override via env var

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Rewrite docker service hostnames to localhost when not in Docker,
        # so the same env files work both in docker-compose and on the host.
        if os.getenv("DOCKER_ENV") != "true":
            self.DATABASE_URL = rewrite_host(self.DATABASE_URL, "postgres")
            self.VALKEY_URL = rewrite_host(self.VALKEY_URL, "valkey")

    model_config = SettingsConfigDict(
        env_file=get_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
