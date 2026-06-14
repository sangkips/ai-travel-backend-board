"""Notification ORM model.

Created when someone reviews a place that was added by a different user.
The place creator is notified via in-app polling (MVP) or push (v2).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from src.models.places import Place
    from src.models.reviews import Review
    from src.models.users import User


class Notification(Base):
    """An in-app alert sent to a place's creator when their place gets reviewed."""

    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Recipient: the user who originally added the place
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    place_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("places.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    review_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
    )

    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True, nullable=True)

    # Relationships
    user: Mapped[User] = relationship(back_populates="notifications", lazy="noload")
    place: Mapped[Place] = relationship(back_populates="notifications", lazy="noload")
    review: Mapped[Review] = relationship(back_populates="notifications", lazy="noload")
