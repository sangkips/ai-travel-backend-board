import redis.asyncio as redis

from src.settings import settings

# VALKEY_URL = os.getenv('VALKEY_URL', 'redis://localhost:6379/0')


async def get_valkey():
    client = redis.from_url(settings.VALKEY_URL, decode_responses=True)

    try:
        yield client

    finally:
        await client.aclose()
