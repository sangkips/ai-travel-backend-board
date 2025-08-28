from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

class HealthRepository:
    def __init__(self, db: AsyncSession, valkey_client: redis.Redis):
        self.db = db
        self.valkey_client = valkey_client

    async def get_status(self) -> str:
        cached_status = await self.valkey_client.get("health_status")
        if cached_status:
            return cached_status

        # Check database connection
        try:
            await self.db.execute(text("SELECT 1"))
            status = "healthy"
        except Exception:
            status = "unhealthy"

        # Cache the status in Valkey for 60 seconds
        await self.valkey_client.set("health_status", status, ex=60)
        return status
