"""Vote ORM model.

Records a single upvote or downvote on a review.
The unique constraint prevents a user from voting twice on the same review.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from src.models.reviews import Review
    from src.models.users import User


class Vote(Base):
    """A single upvote or downvote cast by a user on a review."""

    __tablename__ = "votes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_upvote: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=True)

    # Relationships
    review: Mapped[Review] = relationship(back_populates="votes", lazy="noload")
    user: Mapped[User] = relationship(back_populates="votes", lazy="noload")

    __table_args__ = (UniqueConstraint("review_id", "user_id", name="uq_vote_review_user"),)
