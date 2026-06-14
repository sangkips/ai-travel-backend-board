"""GraphQL request context factory.

Injects the database session and authenticated user (if any) into every
GraphQL resolver via ``info.context``. Resolvers access them as:

    db: AsyncSession = info.context["db"]
    user: dict | None = info.context["current_user"]  # None if unauthenticated
"""

import uuid

import redis.asyncio as redis
from fastapi import Depends
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import HTTPConnection

from src.database import get_db
from src.services.auth_service import decode_token
from src.valkey_client import get_valkey


def _user_from_token(token: str) -> dict | None:
    """Decode a bearer token into ``{"user_id", "role"}`` or ``None``."""
    if not token:
        return None
    try:
        payload = decode_token(token)
        return {"user_id": uuid.UUID(payload["sub"]), "role": payload["role"]}
    except (JWTError, KeyError, ValueError):
        return None


async def get_graphql_context(
    request: HTTPConnection,
    db: AsyncSession = Depends(get_db),
    valkey: redis.Redis = Depends(get_valkey),
) -> dict:
    """Build the context dict passed to every Strawberry resolver.

    Authentication is optional at the context level: if a valid ``Bearer``
    token is present it is decoded into ``current_user``; otherwise that key is
    ``None``. Individual resolvers that require auth call ``require_auth`` (see
    below). An invalid/expired token is treated as unauthenticated rather than
    an error, so public resolvers still work.
    """
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    current_user = _user_from_token(token) if scheme.lower() == "bearer" else None
    return {"db": db, "current_user": current_user, "valkey": valkey}


def user_from_context(context: dict) -> dict | None:
    """Resolve the authenticated user for any operation type.

    Queries/mutations carry auth in the HTTP ``Authorization`` header (already
    decoded into ``current_user``). WebSocket subscriptions can't set headers,
    so clients send the token in the ``connection_init`` payload, which
    Strawberry exposes as ``context["connection_params"]``. Accepts either an
    ``Authorization: Bearer <t>`` entry or a bare ``token`` key.
    """
    if context.get("current_user"):
        return context["current_user"]
    params = context.get("connection_params") or {}
    auth = params.get("Authorization") or params.get("authorization") or ""
    token = auth.removeprefix("Bearer ").removeprefix("bearer ").strip()
    return _user_from_token(token or params.get("token", ""))


def require_auth(context: dict) -> dict:
    """Extract current_user from context; raise ValueError if not authenticated.

    Usage inside a resolver:
        user = require_auth(info.context)
    """
    user = context.get("current_user")
    if user is None:
        raise ValueError("Authentication required")
    return user
