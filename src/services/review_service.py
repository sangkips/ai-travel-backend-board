"""Review service – the core business loop of the MVP.

Flow for create_review:
  1. Insert the Review row.
  2. Refresh denormalised aggregates on the parent Place.
  3. If the reviewer is not the place creator → insert a Notification.
  4. Return the ReviewOut schema.
"""

import uuid

from src.models.notifications import Notification
from src.models.reviews import Review
from src.repositories.notification_repository import NotificationRepository
from src.repositories.place_repository import PlaceRepository
from src.repositories.review_repository import ReviewRepository
from src.schemas.reviews import CreateReviewInput, ReviewOut


class ReviewService:
    """Handles review creation, listing, and related side-effects."""

    def __init__(
        self,
        review_repo: ReviewRepository,
        place_repo: PlaceRepository,
        notification_repo: NotificationRepository,
    ) -> None:
        self._reviews = review_repo
        self._places = place_repo
        self._notifications = notification_repo

    async def create_review(
        self,
        data: CreateReviewInput,
        author_id: uuid.UUID,
        author_role: str,
    ) -> ReviewOut:
        """Submit a review and trigger all downstream side-effects.

        Raises ValueError if the place does not exist.
        """
        from src.models.enums import UserRole  # local import avoids circular dep

        place = await self._places.get_by_id(data.place_id)
        if place is None:
            raise ValueError(f"Place {data.place_id} not found")

        review = Review(
            place_id=data.place_id,
            author_id=author_id,
            role_at_time=UserRole(author_role),
            safety_score=data.safety_score,
            tourism_type=data.tourism_type,
            text=data.text,
        )
        review = await self._reviews.create(review)

        # Refresh denormalised columns on the Place row
        await self._places.refresh_aggregates(data.place_id)

        # Notify the place creator if they didn't write this review themselves
        if place.created_by_id and place.created_by_id != author_id:
            notif = Notification(
                user_id=place.created_by_id,
                place_id=place.id,
                review_id=review.id,
            )
            await self._notifications.create(notif)

        return self._to_out(review)

    async def get_place_reviews(
        self,
        place_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> list[ReviewOut]:
        """Return paginated reviews for a place."""
        reviews = await self._reviews.get_by_place(place_id, limit=limit, offset=offset)
        return [self._to_out(r) for r in reviews]

    async def get_my_reviews(self, author_id: uuid.UUID) -> list[ReviewOut]:
        """Return reviews written by the authenticated user."""
        reviews = await self._reviews.get_by_author(author_id)
        return [self._to_out(r) for r in reviews]

    @staticmethod
    def _to_out(review: Review) -> ReviewOut:
        return ReviewOut(
            id=review.id,
            place_id=review.place_id,
            author_id=review.author_id,
            author_name=None,  # Populated by join in v2
            role_at_time=review.role_at_time,
            safety_score=review.safety_score,
            tourism_type=review.tourism_type,
            text=review.text,
            upvote_count=review.upvote_count,
            downvote_count=review.downvote_count,
            created_at=review.created_at,
        )
