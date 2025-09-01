from fastapi import FastAPI

from src.api.routers.health import router as health_router

app = FastAPI(
    title="AI Travel Management App",
    description="AI Travel application",
    version="0.1.0",
)

app.include_router(health_router, prefix="/api/v1")
