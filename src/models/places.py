"""Place ORM model.

A place is a named, geolocated point of interest that any user can add.
The creator receives notifications when others leave reviews.
PostGIS ``POINT`` geometry is used for efficient spatial queries.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from geoalchemy2 import Geometry
from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.models.enums import TourismType

if TYPE_CHECKING:
    from src.models.notifications import Notification
    from src.models.reviews import Review
    from src.models.users import User


class Place(Base):
    """A named location that users can review for safety and tourism type."""

    __tablename__ = "places"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)

    # PostGIS POINT(lng lat), SRID 4326 (WGS84)
    location: Mapped[Any] = mapped_column(Geometry("POINT", srid=4326), nullable=False)

    # Convenience scalar columns for non-spatial queries / display
    address: Mapped[str | None] = mapped_column(String, nullable=True)
    city: Mapped[str | None] = mapped_column(String, nullable=True)
    country: Mapped[str | None] = mapped_column(String, nullable=True)

    # Who added this place (the "discoverer")
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Denormalised aggregates – updated on every new review
    average_safety_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_reviews: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    dominant_tourism_type: Mapped[TourismType | None] = mapped_column(
        Enum(TourismType, name="tourism_type"), nullable=True
    )
    last_review_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True
    )

    # Relationships
    created_by: Mapped[User | None] = relationship(back_populates="places", lazy="noload")
    reviews: Mapped[list[Review]] = relationship(back_populates="place", lazy="noload", cascade="all, delete-orphan")
    notifications: Mapped[list[Notification]] = relationship(
        back_populates="place",
        lazy="noload",
        cascade="all, delete-orphan",
    )

    __table_args__ = (UniqueConstraint("name", "created_by_id", name="uq_place_name_creator"),)
