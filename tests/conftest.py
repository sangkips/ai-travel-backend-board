"""Shared pytest fixtures.

The end-to-end tests run the FastAPI app in-process (via httpx's ASGI
transport) against a real Postgres/PostGIS + Valkey, which CI provides as
service containers. When those backends aren't reachable (e.g. a local run
without the stack up), the dependent fixtures ``skip`` rather than fail.
"""

import os

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DOCKER_ENV", "false")

import httpx
import pytest_asyncio
import redis.asyncio as redis
from httpx import ASGITransport
from sqlalchemy import text

import src.models  # noqa: F401 -- registers every model on Base.metadata
from src.database import Base, engine
from src.main import app
from src.settings import settings


@pytest_asyncio.fixture
async def db_schema():
    """Create PostGIS + all tables in the test DB; skip if it's unreachable."""
    import pytest

    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:  # noqa: BLE001 -- any connection/setup failure → skip
        pytest.skip(f"test database not available: {exc}")
    yield


@pytest_asyncio.fixture
async def valkey_up():
    """Ensure Valkey is reachable (event publishing needs it); skip otherwise."""
    import pytest

    client = redis.from_url(settings.VALKEY_URL, decode_responses=True)
    try:
        await client.ping()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"valkey not available: {exc}")
    finally:
        await client.aclose()
    yield


@pytest_asyncio.fixture
async def client(db_schema, valkey_up):
    """An httpx client wired to the app in-process (no running server needed)."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c
