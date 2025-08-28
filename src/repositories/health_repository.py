from pydoc import text
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

class HealthRepository:
    def __init__(self, db: AsyncSession, valkey_client: redis.Redis):
        self.db = db
        self.valkey_client = valkey_client

    async def get_status(self) -> str:
        # Check Valkey cache first
        cached_status = await self.valkey_client.get("health_status")
        if cached_status:
            return cached_status

    async def get_status(self) -> str:
        try:
            await self.db.execute(text("SELECT 1"))
            return "healthy"
        except Exception:
            return "unhealthy"
