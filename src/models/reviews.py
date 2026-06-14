"""Review ORM model.

A review captures a user's safety score and tourism-type classification
for a specific place. The reviewer's role is snapshotted at write time so
it remains accurate even if the user changes their role later.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    SmallInteger,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.models.enums import TourismType, UserRole

if TYPE_CHECKING:
    from src.models.notifications import Notification
    from src.models.places import Place
    from src.models.users import User
    from src.models.votes import Vote


class Review(Base):
    """A safety-focused review of a place, anchored to the reviewer's role."""

    __tablename__ = "reviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    place_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("places.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Snapshot of the reviewer's role at the time of writing
    role_at_time: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), nullable=False)

    # Core safety rating (1–5)
    safety_score: Mapped[int] = mapped_column(
        SmallInteger,
        CheckConstraint("safety_score BETWEEN 1 AND 5", name="chk_safety_score"),
        nullable=False,
    )

    # Primary tourism classification for this review
    tourism_type: Mapped[TourismType] = mapped_column(Enum(TourismType, name="tourism_type"), nullable=False)

    # Optional free-text body
    text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Net reputation signals
    upvote_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    downvote_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True
    )

    # Relationships
    place: Mapped[Place] = relationship(back_populates="reviews", lazy="noload")
    author: Mapped[User | None] = relationship(back_populates="reviews", lazy="noload")
    votes: Mapped[list[Vote]] = relationship(back_populates="review", lazy="noload", cascade="all, delete-orphan")
    notifications: Mapped[list[Notification]] = relationship(
        back_populates="review",
        lazy="noload",
        cascade="all, delete-orphan",
    )
