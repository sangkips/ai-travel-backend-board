"""Strawberry GraphQL schema.

Enums are imported from ``src.models.enums`` (real Python enum.Enum subclasses)
and wrapped with ``strawberry.enum`` so they become valid GraphQL enum types.

Object types mirror the REST schemas but use Strawberry annotations.
All resolvers delegate to the same service layer used by the REST routers.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator
from datetime import datetime

import strawberry
from strawberry.types import Info

from graphql import GraphQLError
from src.models.enums import SafetyLabel, TourismType, UserRole
from src.repositories.notification_repository import NotificationRepository
from src.repositories.place_repository import PlaceRepository
from src.repositories.review_repository import ReviewRepository
from src.repositories.user_repository import UserRepository
from src.repositories.vote_repository import VoteRepository
from src.schemas.auth import LoginInput as LoginSchema
from src.schemas.auth import SignUpInput as SignUpSchema
from src.schemas.places import CreatePlaceInput as CreatePlaceSchema
from src.schemas.reviews import CreateReviewInput as CreateReviewSchema
from src.schemas.reviews import VoteInput as VoteSchema
from src.services.auth_service import AuthService
from src.services.notification_service import NotificationService
from src.services.place_service import PlaceService
from src.services.review_service import ReviewService
from src.services.vote_service import VoteService

# ---------------------------------------------------------------------------
# ENUMS  (wrap real Python enums — this is what Strawberry requires)
# ---------------------------------------------------------------------------
GQLUserRole = strawberry.enum(UserRole)
GQLTourismType = strawberry.enum(TourismType)
GQLSafetyLabel = strawberry.enum(SafetyLabel)


# ---------------------------------------------------------------------------
# OBJECT TYPES
# ---------------------------------------------------------------------------
@strawberry.type
class GQLUser:
    """Public user profile."""

    id: strawberry.ID
    name: str
    role: GQLUserRole  # type: ignore[valid-type]
    reputation_score: float
    is_verified: bool
    created_at: datetime


@strawberry.type
class GQLPlace:
    """A named, geolocated place with aggregated safety data."""

    id: strawberry.ID
    name: str
    lat: float
    lng: float
    address: str | None
    city: str | None
    country: str | None
    average_safety_score: float
    safety_label: GQLSafetyLabel  # type: ignore[valid-type]
    total_reviews: int
    dominant_tourism_type: GQLTourismType | None  # type: ignore[valid-type]
    created_by_id: strawberry.ID | None
    is_discovered_by_me: bool
    last_review_at: datetime | None
    created_at: datetime
    distance_km: float | None = None  # Only set by nearby_places


@strawberry.type
class GQLReview:
    """A safety-focused review of a place."""

    id: strawberry.ID
    place_id: strawberry.ID
    author_id: strawberry.ID | None
    author_name: str | None
    role_at_time: GQLUserRole  # type: ignore[valid-type]
    safety_score: int
    tourism_type: GQLTourismType  # type: ignore[valid-type]
    text: str | None
    upvote_count: int
    downvote_count: int
    my_vote: bool | None
    created_at: datetime


@strawberry.type
class GQLNotification:
    """In-app alert sent to a place creator when their place is reviewed."""

    id: strawberry.ID
    place_id: strawberry.ID
    place_name: str | None
    review_id: strawberry.ID
    reviewer_role: GQLUserRole | None  # type: ignore[valid-type]
    is_read: bool
    created_at: datetime


@strawberry.type
class GQLToken:
    """JWT bearer token returned after successful authentication."""

    access_token: str
    token_type: str


# ---------------------------------------------------------------------------
# INPUT TYPES
# ---------------------------------------------------------------------------
@strawberry.input
class SignUpInput:
    """Registration payload."""

    name: str
    email: str
    phone: str | None = None
    role: GQLUserRole  # type: ignore[valid-type]
    password: str


@strawberry.input
class LoginInput:
    """Login payload."""

    email: str
    password: str


@strawberry.input
class CreatePlaceInput:
    """Payload for adding a new place."""

    name: str
    lat: float
    lng: float
    address: str | None = None
    city: str | None = None
    country: str | None = None


@strawberry.input
class CreateReviewInput:
    """Payload for submitting a review."""

    place_id: uuid.UUID
    safety_score: int  # 1–5
    tourism_type: GQLTourismType  # type: ignore[valid-type]
    text: str | None = None


@strawberry.input
class VoteInput:
    """Payload for casting a vote."""

    review_id: uuid.UUID
    is_upvote: bool


# ---------------------------------------------------------------------------
# HELPERS  (auth guard + ORM/schema → GraphQL type mappers)
# ---------------------------------------------------------------------------
def _require_user(info: Info) -> dict:
    """Return the authenticated user from context or raise a GraphQL error.

    ``current_user`` is ``{"user_id": UUID, "role": str}`` (see
    ``get_graphql_context``).
    """
    user = info.context.get("current_user")
    if user is None:
        raise GraphQLError("Authentication required")
    return user


def _gql_user(u) -> GQLUser:
    return GQLUser(
        id=strawberry.ID(str(u.id)),
        name=u.name,
        role=u.role,
        reputation_score=u.reputation_score,
        is_verified=u.is_verified,
        created_at=u.created_at,
    )


def _gql_place(p) -> GQLPlace:
    """Map a ``PlaceOut`` or ``PlaceListItem`` to ``GQLPlace``.

    List items lack the detail-only fields, so those fall back to None/False.
    """
    created_by = getattr(p, "created_by_id", None)
    return GQLPlace(
        id=strawberry.ID(str(p.id)),
        name=p.name,
        lat=p.lat,
        lng=p.lng,
        address=getattr(p, "address", None),
        city=p.city,
        country=p.country,
        average_safety_score=p.average_safety_score,
        safety_label=p.safety_label,
        total_reviews=p.total_reviews,
        dominant_tourism_type=p.dominant_tourism_type,
        created_by_id=strawberry.ID(str(created_by)) if created_by else None,
        is_discovered_by_me=getattr(p, "is_discovered_by_me", False),
        last_review_at=getattr(p, "last_review_at", None),
        created_at=p.created_at,
        distance_km=getattr(p, "distance_km", None),
    )


def _gql_review(r) -> GQLReview:
    return GQLReview(
        id=strawberry.ID(str(r.id)),
        place_id=strawberry.ID(str(r.place_id)),
        author_id=strawberry.ID(str(r.author_id)) if r.author_id else None,
        author_name=r.author_name,
        role_at_time=r.role_at_time,
        safety_score=r.safety_score,
        tourism_type=r.tourism_type,
        text=r.text,
        upvote_count=r.upvote_count,
        downvote_count=r.downvote_count,
        my_vote=r.my_vote,
        created_at=r.created_at,
    )


def _gql_notification(n) -> GQLNotification:
    return GQLNotification(
        id=strawberry.ID(str(n.id)),
        place_id=strawberry.ID(str(n.place_id)),
        place_name=n.place_name,
        review_id=strawberry.ID(str(n.review_id)),
        reviewer_role=n.reviewer_role,
        is_read=n.is_read,
        created_at=n.created_at,
    )


# ---------------------------------------------------------------------------
# QUERY RESOLVERS
# ---------------------------------------------------------------------------
@strawberry.type
class Query:
    """Read-only queries."""

    @strawberry.field
    async def me(self, info: Info) -> GQLUser | None:
        """Return the currently authenticated user, or null if unauthenticated."""
        user = info.context.get("current_user")
        if user is None:
            return None
        service = AuthService(UserRepository(info.context["db"]))
        try:
            profile = await service.get_current_user(str(user["user_id"]))
        except ValueError:
            return None
        return _gql_user(profile)

    @strawberry.field
    async def place(self, info: Info, place_id: strawberry.ID) -> GQLPlace | None:
        """Return a single place by ID."""
        user = info.context.get("current_user")
        service = PlaceService(PlaceRepository(info.context["db"]))
        place = await service.get_place(
            uuid.UUID(place_id),
            current_user_id=user["user_id"] if user else None,
        )
        return _gql_place(place) if place else None

    @strawberry.field
    async def nearby_places(
        self,
        info: Info,
        lat: float,
        lng: float,
        radius_km: float = 10.0,
        min_safety_score: float | None = None,
        tourism_type: GQLTourismType | None = None,  # type: ignore[valid-type]
        limit: int = 20,
        offset: int = 0,
    ) -> list[GQLPlace]:
        """Return places within radius_km ordered by distance."""
        user = info.context.get("current_user")
        service = PlaceService(PlaceRepository(info.context["db"]))
        items = await service.get_nearby(
            lat=lat,
            lng=lng,
            radius_km=radius_km,
            min_safety_score=min_safety_score,
            tourism_type=tourism_type.value if tourism_type else None,
            limit=limit,
            offset=offset,
            current_user_id=user["user_id"] if user else None,
        )
        return [_gql_place(i) for i in items]

    @strawberry.field
    async def place_reviews(
        self,
        info: Info,
        place_id: strawberry.ID,
        limit: int = 20,
        offset: int = 0,
    ) -> list[GQLReview]:
        """Return reviews for a place, newest first."""
        service = ReviewService(
            ReviewRepository(info.context["db"]),
            PlaceRepository(info.context["db"]),
            NotificationRepository(info.context["db"]),
        )
        reviews = await service.get_place_reviews(uuid.UUID(place_id), limit=limit, offset=offset)
        return [_gql_review(r) for r in reviews]

    @strawberry.field
    async def my_reviews(self, info: Info, limit: int = 20) -> list[GQLReview]:
        """Return reviews written by the authenticated user."""
        user = _require_user(info)
        service = ReviewService(
            ReviewRepository(info.context["db"]),
            PlaceRepository(info.context["db"]),
            NotificationRepository(info.context["db"]),
        )
        reviews = await service.get_my_reviews(user["user_id"])
        return [_gql_review(r) for r in reviews[:limit]]

    @strawberry.field
    async def my_places(self, info: Info) -> list[GQLPlace]:
        """Return places added by the authenticated user."""
        user = _require_user(info)
        service = PlaceService(PlaceRepository(info.context["db"]))
        places = await service.get_my_places(user["user_id"])
        return [_gql_place(p) for p in places]

    @strawberry.field
    async def notifications(
        self,
        info: Info,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[GQLNotification]:
        """Return in-app notifications for the authenticated user."""
        user = _require_user(info)
        service = NotificationService(NotificationRepository(info.context["db"]))
        notifs = await service.get_notifications(user_id=user["user_id"], unread_only=unread_only, limit=limit)
        return [_gql_notification(n) for n in notifs]


# ---------------------------------------------------------------------------
# MUTATION RESOLVERS
# ---------------------------------------------------------------------------
@strawberry.type
class Mutation:
    """Write operations."""

    @strawberry.mutation
    async def sign_up(self, info: Info, data: SignUpInput) -> GQLToken:
        """Register a new user and return a JWT."""
        service = AuthService(UserRepository(info.context["db"]))
        try:
            token = await service.sign_up(
                SignUpSchema(
                    name=data.name,
                    email=data.email,
                    phone=data.phone,
                    role=data.role,
                    password=data.password,
                )
            )
        except ValueError as exc:
            raise GraphQLError(str(exc)) from exc
        return GQLToken(access_token=token.access_token, token_type=token.token_type)

    @strawberry.mutation
    async def login(self, info: Info, data: LoginInput) -> GQLToken:
        """Authenticate and return a JWT."""
        service = AuthService(UserRepository(info.context["db"]))
        try:
            token = await service.login(LoginSchema(email=data.email, password=data.password))
        except ValueError as exc:
            raise GraphQLError(str(exc)) from exc
        return GQLToken(access_token=token.access_token, token_type=token.token_type)

    @strawberry.mutation
    async def create_place(self, info: Info, data: CreatePlaceInput) -> GQLPlace:
        """Add a new place to the map."""
        user = _require_user(info)
        service = PlaceService(PlaceRepository(info.context["db"]))
        try:
            place = await service.create_place(
                CreatePlaceSchema(
                    name=data.name,
                    lat=data.lat,
                    lng=data.lng,
                    address=data.address,
                    city=data.city,
                    country=data.country,
                ),
                created_by_id=user["user_id"],
            )
        except ValueError as exc:
            raise GraphQLError(str(exc)) from exc
        return _gql_place(place)

    @strawberry.mutation
    async def create_review(self, info: Info, data: CreateReviewInput) -> GQLReview:
        """Submit a safety review for a place."""
        user = _require_user(info)
        service = ReviewService(
            ReviewRepository(info.context["db"]),
            PlaceRepository(info.context["db"]),
            NotificationRepository(info.context["db"]),
        )
        try:
            review = await service.create_review(
                data=CreateReviewSchema(
                    place_id=data.place_id,
                    safety_score=data.safety_score,
                    tourism_type=data.tourism_type,
                    text=data.text,
                ),
                author_id=user["user_id"],
                author_role=user["role"],
            )
        except ValueError as exc:
            raise GraphQLError(str(exc)) from exc
        return _gql_review(review)

    @strawberry.mutation
    async def vote_review(self, info: Info, data: VoteInput) -> GQLReview:
        """Upvote or downvote a review."""
        user = _require_user(info)
        service = VoteService(
            VoteRepository(info.context["db"]),
            ReviewRepository(info.context["db"]),
            UserRepository(info.context["db"]),
        )
        try:
            review = await service.cast_vote(
                review_id=data.review_id,
                voter_id=user["user_id"],
                data=VoteSchema(is_upvote=data.is_upvote),
            )
        except ValueError as exc:
            raise GraphQLError(str(exc)) from exc
        return _gql_review(review)

    @strawberry.mutation
    async def mark_notification_read(self, info: Info, notification_id: uuid.UUID) -> bool:
        """Mark a single notification as read.

        Returns ``True`` if a notification owned by the caller was updated.
        """
        user = _require_user(info)
        service = NotificationService(NotificationRepository(info.context["db"]))
        return await service.mark_read(notification_id, user["user_id"])


# ---------------------------------------------------------------------------
# SUBSCRIPTION RESOLVERS (placeholder — enable in v2 with Redis pub/sub)
# ---------------------------------------------------------------------------
@strawberry.type
class Subscription:
    """Real-time subscriptions (stubbed; wire to Valkey pub/sub in v2)."""

    @strawberry.subscription
    async def review_added_to_my_place(
        self,
        info: Info,
        place_id: strawberry.ID | None = None,
    ) -> AsyncIterator[GQLReview]:
        """Fires when someone reviews a place you created."""
        # Stub: never emits. Wire to Valkey pub/sub in v2.
        while True:
            await asyncio.sleep(3600)
        yield  # unreachable; makes this resolver an async generator

    @strawberry.subscription
    async def place_security_alert(
        self,
        info: Info,
        place_id: strawberry.ID,
    ) -> AsyncIterator[GQLPlace]:
        """Fires when a place's safety label changes."""
        # Stub: never emits. Wire to Valkey pub/sub in v2.
        while True:
            await asyncio.sleep(3600)
        yield  # unreachable; makes this resolver an async generator


# ---------------------------------------------------------------------------
# SCHEMA CONSTRUCTION
# ---------------------------------------------------------------------------
schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    subscription=Subscription,
)
