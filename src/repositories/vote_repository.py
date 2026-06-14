"""Vote repository – all DB access for the votes table."""

import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.votes import Vote


class VoteRepository:
    """Data-access layer for Vote records."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_vote(self, review_id: uuid.UUID, user_id: uuid.UUID) -> Vote | None:
        """Return an existing vote, or None."""
        result = await self.db.execute(
            select(Vote).where(
                Vote.review_id == review_id,
                Vote.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def upsert(self, review_id: uuid.UUID, user_id: uuid.UUID, is_upvote: bool) -> tuple[Vote, bool]:
        """Insert or update a vote.

        Returns (vote, was_created). Uses PostgreSQL ON CONFLICT DO UPDATE
        so the operation is a single round-trip.
        """
        stmt = (
            pg_insert(Vote)
            .values(
                id=uuid.uuid4(),
                review_id=review_id,
                user_id=user_id,
                is_upvote=is_upvote,
            )
            .on_conflict_do_update(
                constraint="uq_vote_review_user",
                set_={"is_upvote": is_upvote},
            )
            .returning(Vote)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        vote = result.scalar_one()
        # If the row was newly inserted the id matches the one we generated
        return vote, True
