"""Place-related Pydantic schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator

from src.models.enums import SafetyLabel, TourismType


class CreatePlaceInput(BaseModel):
    """Payload for adding a new place to the map."""

    name: str
    lat: float
    lng: float
    address: str | None = None
    city: str | None = None
    country: str | None = None

    @field_validator("lat")
    @classmethod
    def validate_lat(cls, v: float) -> float:
        """Latitude must be in range [-90, 90]."""
        if not (-90 <= v <= 90):
            raise ValueError("Latitude must be between -90 and 90")
        return v

    @field_validator("lng")
    @classmethod
    def validate_lng(cls, v: float) -> float:
        """Longitude must be in range [-180, 180]."""
        if not (-180 <= v <= 180):
            raise ValueError("Longitude must be between -180 and 180")
        return v


class PlaceListItem(BaseModel):
    """Lightweight place representation used in list/nearby responses."""

    id: uuid.UUID
    name: str
    lat: float
    lng: float
    city: str | None
    country: str | None
    average_safety_score: float
    safety_label: SafetyLabel
    total_reviews: int
    dominant_tourism_type: TourismType | None
    distance_km: float | None = None  # Only set in nearby queries
    created_at: datetime

    model_config = {"from_attributes": True}


class PlaceOut(PlaceListItem):
    """Full place representation including discoverer info."""

    address: str | None
    created_by_id: uuid.UUID | None
    last_review_at: datetime | None
    is_discovered_by_me: bool = False  # Set in the service layer


def compute_safety_label(avg: float) -> SafetyLabel:
    """Derive a traffic-light safety label from the average safety score."""
    if avg >= 4.0:
        return SafetyLabel.SAFE
    if avg >= 2.5:
        return SafetyLabel.CAUTION
    return SafetyLabel.AVOID
