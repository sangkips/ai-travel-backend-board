"""Notification-related Pydantic schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel

from src.models.enums import UserRole


class NotificationOut(BaseModel):
    """In-app notification sent to a place creator when their place gets reviewed."""

    id: uuid.UUID
    place_id: uuid.UUID
    place_name: str | None  # Eagerly joined in the repository
    review_id: uuid.UUID
    reviewer_role: UserRole | None  # Snapshot from the triggering review
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}
