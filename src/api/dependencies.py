from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.valkey_client import get_valkey
from src.database import get_db
from src.repositories.health_repository import HealthRepository
from src.services.health_service import HealthService
import redis.asyncio as redis

def get_health_service(db: AsyncSession = Depends(get_db), valkey_client: redis.Redis = Depends(get_valkey)) -> HealthService:
    repository = HealthRepository(db, valkey_client)
    return HealthService(repository)
