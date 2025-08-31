from datetime import UTC, datetime

from src.repositories.health_repository import HealthRepository
from src.schemas.health_schema import HealthResponse


class HealthService:
    def __init__(self, repository: HealthRepository):
        self.repository = repository

    async def check_health(self) -> HealthResponse:
        status = await self.repository.get_status()
        return HealthResponse(
            status=status,
            timestamp=datetime.now(UTC),
        )
