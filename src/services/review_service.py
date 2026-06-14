"""Review service – the core business loop of the MVP.

Flow for create_review:
  1. Insert the Review row.
  2. Refresh denormalised aggregates on the parent Place.
  3. If the reviewer is not the place creator → insert a Notification.
  4. Return the ReviewOut schema.
"""

import uuid

import redis.asyncio as redis

from src.events import (
    place_security_channel,
    publish,
    review_added_channel,
)
from src.models.notifications import Notification
from src.models.reviews import Review
from src.repositories.notification_repository import NotificationRepository
from src.repositories.place_repository import PlaceRepository
from src.repositories.review_repository import ReviewRepository
from src.schemas.places import compute_safety_label
from src.schemas.reviews import CreateReviewInput, ReviewOut
from src.services.place_service import PlaceService


class ReviewService:
    """Handles review creation, listing, and related side-effects."""

    def __init__(
        self,
        review_repo: ReviewRepository,
        place_repo: PlaceRepository,
        notification_repo: NotificationRepository,
        valkey: redis.Redis | None = None,
    ) -> None:
        self._reviews = review_repo
        self._places = place_repo
        self._notifications = notification_repo
        # Optional: when provided, real-time events are published for the
        # GraphQL subscriptions. REST/GraphQL both inject it (see dependencies
        # and the GraphQL context), so events fire regardless of entry point.
        self._valkey = valkey

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

        # Capture the safety label *before* this review shifts the aggregate.
        old_label = compute_safety_label(place.average_safety_score)

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

        review_out = self._to_out(review)
        await self._publish_events(place, author_id, review_out, old_label)
        return review_out

    async def _publish_events(
        self,
        place,
        author_id: uuid.UUID,
        review_out: ReviewOut,
        old_label,
    ) -> None:
        """Emit real-time events for GraphQL subscriptions (best-effort)."""
        if self._valkey is None:
            return

        # 1. Tell the place creator's stream a new review arrived.
        if place.created_by_id and place.created_by_id != author_id:
            await publish(
                self._valkey,
                review_added_channel(place.created_by_id),
                review_out.model_dump(mode="json"),
            )

        # 2. If this review changed the place's safety label, alert watchers.
        updated = await self._places.get_by_id(place.id)
        if updated is None:
            return
        new_label = compute_safety_label(updated.average_safety_score)
        if new_label != old_label:
            place_out = PlaceService(self._places)._to_place_out(updated)
            await publish(
                self._valkey,
                place_security_channel(place.id),
                place_out.model_dump(mode="json"),
            )

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
