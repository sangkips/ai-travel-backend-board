from fastapi import APIRouter, Depends
from src.schemas.health_schema import HealthResponse
from src.services.health_service import HealthService
from src.api.dependencies import get_health_service

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def health_check(service: HealthService = Depends(get_health_service)):
    return await service.check_health()
