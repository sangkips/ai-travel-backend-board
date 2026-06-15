"""Review-related Pydantic schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from src.models.enums import TourismType, UserRole


class CreateReviewInput(BaseModel):
    """Payload for submitting a review on an existing place."""

    place_id: uuid.UUID
    safety_score: int = Field(..., ge=1, le=5, description="Safety rating from 1 (avoid) to 5 (very safe)")
    tourism_type: TourismType
    text: str | None = None


class ReviewOut(BaseModel):
    """Review representation returned in API responses."""

    id: uuid.UUID
    place_id: uuid.UUID
    author_id: uuid.UUID | None
    author_name: str | None
    role_at_time: UserRole
    safety_score: int
    tourism_type: TourismType
    text: str | None
    upvote_count: int
    downvote_count: int
    my_vote: bool | None = None  # True=upvoted, False=downvoted, None=no vote
    created_at: datetime

    model_config = {"from_attributes": True}


class VoteInput(BaseModel):
    """Payload for casting or changing a vote on a review."""

    is_upvote: bool
