import os
import redis.asyncio as redis


VALKEY_URL = os.getenv('VALKEY_URL', 'redis://localhost:6379/0')

async def get_valkey():
    client = redis.from_url(VALKEY_URL, decode_response=True)

    try:
        yield client

    finally:
        await client.aclose()
