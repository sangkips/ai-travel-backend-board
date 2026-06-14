"""FastAPI dependency injection factory functions.

Every new service must have a factory function here. Routers declare their
service dependency via ``Depends(get_<name>_service)`` – they never
instantiate services or repositories directly.
"""

import uuid

import redis.asyncio as redis
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.repositories.health_repository import HealthRepository
from src.repositories.notification_repository import NotificationRepository
from src.repositories.place_repository import PlaceRepository
from src.repositories.review_repository import ReviewRepository
from src.repositories.user_repository import UserRepository
from src.repositories.vote_repository import VoteRepository
from src.services.auth_service import AuthService, decode_token
from src.services.health_service import HealthService
from src.services.notification_service import NotificationService
from src.services.place_service import PlaceService
from src.services.review_service import ReviewService
from src.services.vote_service import VoteService
from src.valkey_client import get_valkey

_bearer = HTTPBearer()


# ---------------------------------------------------------------------------
# Existing health service (unchanged)
# ---------------------------------------------------------------------------
def get_health_service(
    db: AsyncSession = Depends(get_db),
    valkey_client: redis.Redis = Depends(get_valkey),
) -> HealthService:
    repository = HealthRepository(db, valkey_client)
    return HealthService(repository)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """Return an AuthService backed by a UserRepository."""
    return AuthService(UserRepository(db))


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Decode the Bearer JWT and return ``{"user_id": UUID, "role": str}``.

    Raises HTTP 401 on any token error so callers never see JWTError.
    """
    try:
        payload = decode_token(credentials.credentials)
        user_id = uuid.UUID(payload["sub"])
        role: str = payload["role"]
    except (JWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"user_id": user_id, "role": role}


# ---------------------------------------------------------------------------
# Place
# ---------------------------------------------------------------------------
def get_place_service(db: AsyncSession = Depends(get_db)) -> PlaceService:
    return PlaceService(PlaceRepository(db))


# ---------------------------------------------------------------------------
# Review
# ---------------------------------------------------------------------------
def get_review_service(db: AsyncSession = Depends(get_db)) -> ReviewService:
    return ReviewService(
        ReviewRepository(db),
        PlaceRepository(db),
        NotificationRepository(db),
    )


# ---------------------------------------------------------------------------
# Vote
# ---------------------------------------------------------------------------
def get_vote_service(db: AsyncSession = Depends(get_db)) -> VoteService:
    return VoteService(
        VoteRepository(db),
        ReviewRepository(db),
        UserRepository(db),
    )


# ---------------------------------------------------------------------------
# Notification
# ---------------------------------------------------------------------------
def get_notification_service(
    db: AsyncSession = Depends(get_db),
) -> NotificationService:
    return NotificationService(NotificationRepository(db))
