"""GraphQL request context factory.

Injects the database session and authenticated user (if any) into every
GraphQL resolver via ``info.context``. Resolvers access them as:

    db: AsyncSession = info.context["db"]
    user: dict | None = info.context["current_user"]  # None if unauthenticated
"""

import uuid

from fastapi import Depends, Request
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.services.auth_service import decode_token


async def get_graphql_context(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Build the context dict passed to every Strawberry resolver.

    Authentication is optional at the context level: if a valid ``Bearer``
    token is present it is decoded into ``current_user``; otherwise that key is
    ``None``. Individual resolvers that require auth call ``require_auth`` (see
    below). An invalid/expired token is treated as unauthenticated rather than
    an error, so public resolvers still work.
    """
    current_user: dict | None = None
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() == "bearer" and token:
        try:
            payload = decode_token(token)
            current_user = {
                "user_id": uuid.UUID(payload["sub"]),
                "role": payload["role"],
            }
        except (JWTError, KeyError, ValueError):
            current_user = None
    return {"db": db, "current_user": current_user}


def require_auth(context: dict) -> dict:
    """Extract current_user from context; raise ValueError if not authenticated.

    Usage inside a resolver:
        user = require_auth(info.context)
    """
    user = context.get("current_user")
    if user is None:
        raise ValueError("Authentication required")
    return user
