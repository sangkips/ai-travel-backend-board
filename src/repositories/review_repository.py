"""Review repository – all DB access for the reviews table."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.reviews import Review


class ReviewRepository:
    """Data-access layer for Review records."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, review: Review) -> Review:
        """Persist a new review and return it with DB-generated fields."""
        self.db.add(review)
        await self.db.commit()
        await self.db.refresh(review)
        return review

    async def get_by_id(self, review_id: uuid.UUID) -> Review | None:
        """Return a review by primary key, or None."""
        result = await self.db.execute(select(Review).where(Review.id == review_id))
        return result.scalar_one_or_none()

    async def get_by_place(
        self,
        place_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Review]:
        """Return reviews for a place ordered from newest to oldest."""
        result = await self.db.execute(
            select(Review)
            .where(Review.place_id == place_id)
            .order_by(Review.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_by_author(
        self,
        author_id: uuid.UUID,
        limit: int = 20,
    ) -> list[Review]:
        """Return reviews written by a specific user."""
        result = await self.db.execute(
            select(Review).where(Review.author_id == author_id).order_by(Review.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())
