"""Vote service – upvote/downvote on reviews with reputation side-effects."""

import uuid

from src.repositories.review_repository import ReviewRepository
from src.repositories.user_repository import UserRepository
from src.repositories.vote_repository import VoteRepository
from src.schemas.reviews import ReviewOut, VoteInput

_REPUTATION_DELTA = 0.5  # Points added/subtracted from author's score per vote


class VoteService:
    """Handles vote upserts and author reputation adjustments."""

    def __init__(
        self,
        vote_repo: VoteRepository,
        review_repo: ReviewRepository,
        user_repo: UserRepository,
    ) -> None:
        self._votes = vote_repo
        self._reviews = review_repo
        self._users = user_repo

    async def cast_vote(
        self,
        review_id: uuid.UUID,
        voter_id: uuid.UUID,
        data: VoteInput,
    ) -> ReviewOut:
        """Cast or update a vote on a review.

        - Prevents self-voting.
        - Adjusts the author's reputation score by ±0.5 per net upvote.
        - Returns the updated ReviewOut.
        """
        review = await self._reviews.get_by_id(review_id)
        if review is None:
            raise ValueError(f"Review {review_id} not found")
        if review.author_id == voter_id:
            raise ValueError("You cannot vote on your own review")

        # Check for an existing vote to determine reputation delta
        existing = await self._votes.get_vote(review_id, voter_id)
        was_upvote_before = existing.is_upvote if existing else None

        await self._votes.upsert(review_id, voter_id, data.is_upvote)

        # Recalculate vote counts in memory before committing
        if data.is_upvote:
            review.upvote_count += 1
            if was_upvote_before is False:
                review.downvote_count = max(0, review.downvote_count - 1)
        else:
            review.downvote_count += 1
            if was_upvote_before is True:
                review.upvote_count = max(0, review.upvote_count - 1)

        # Adjust author reputation
        if review.author_id:
            delta = _REPUTATION_DELTA if data.is_upvote else -_REPUTATION_DELTA
            if was_upvote_before is not None:
                # Changed vote: reverse old effect then apply new
                delta = delta * 2 if was_upvote_before != data.is_upvote else 0.0
            await self._users.update_reputation(review.author_id, delta)

        return ReviewOut(
            id=review.id,
            place_id=review.place_id,
            author_id=review.author_id,
            author_name=None,
            role_at_time=review.role_at_time,
            safety_score=review.safety_score,
            tourism_type=review.tourism_type,
            text=review.text,
            upvote_count=review.upvote_count,
            downvote_count=review.downvote_count,
            my_vote=data.is_upvote,
            created_at=review.created_at,
        )
