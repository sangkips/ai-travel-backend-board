from src.repositories.health_repository import HealthRepository
from src.services.health_service import HealthService

def get_health_service() -> HealthService:
    repository = HealthRepository()
    return HealthService(repository)
