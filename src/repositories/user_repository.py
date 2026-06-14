"""User repository – handles all DB access for the users table."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.users import User


class UserRepository:
    """Data-access layer for User records."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, user: User) -> User:
        """Persist a new user and return it with DB-generated fields populated."""
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Return a user by primary key, or None if not found."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Return a user by email address, or None if not found."""
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def update_reputation(self, user_id: uuid.UUID, delta: float) -> None:
        """Atomically adjust a user's reputation score by delta (+/-)."""
        user = await self.get_by_id(user_id)
        if user:
            user.reputation_score = max(0.0, user.reputation_score + delta)
            await self.db.commit()
