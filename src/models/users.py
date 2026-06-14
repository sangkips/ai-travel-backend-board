from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, Float, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.models.enums import UserRole

if TYPE_CHECKING:
    from src.models.notifications import Notification
    from src.models.places import Place
    from src.models.reviews import Review
    from src.models.votes import Vote


class User(Base):
    """Registered user with a self-declared role."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    reputation_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True
    )

    # Relationships
    places: Mapped[list[Place]] = relationship(back_populates="created_by", lazy="noload")
    reviews: Mapped[list[Review]] = relationship(back_populates="author", lazy="noload")
    votes: Mapped[list[Vote]] = relationship(back_populates="user", lazy="noload")
    notifications: Mapped[list[Notification]] = relationship(back_populates="user", lazy="noload")
