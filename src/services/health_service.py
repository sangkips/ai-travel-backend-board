from datetime import datetime
from src.repositories.health_repository import HealthRepository
from src.schemas.health_schema import HealthResponse

class HealthService:
    def __init__(self, repository: HealthRepository):
        self.repository = repository

    def check_health(self) -> HealthResponse:
        status = self.repository.get_status()
        return HealthResponse(
            status=status,
            timestamp=datetime.utcnow(),
        )
