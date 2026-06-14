"""Notification repository – all DB access for the notifications table."""

import uuid
from typing import cast

from sqlalchemy import CursorResult, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.models.notifications import Notification


class NotificationRepository:
    """Data-access layer for Notification records."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, notification: Notification) -> Notification:
        """Persist a new notification."""
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)
        return notification

    async def get_for_user(
        self,
        user_id: uuid.UUID,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[Notification]:
        """Return notifications for a user, newest first.

        Eagerly loads Place and Review so the service can build rich
        notification payloads without extra queries.
        """
        stmt = (
            select(Notification)
            .options(
                joinedload(Notification.place),
                joinedload(Notification.review),
            )
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        if unread_only:
            stmt = stmt.where(Notification.is_read.is_(False))

        result = await self.db.execute(stmt)
        return list(result.unique().scalars().all())

    async def mark_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Mark a single notification as read.

        Scoped to user_id so a user cannot mark someone else's notification.
        Returns True if a row was updated.
        """
        result = await self.db.execute(
            update(Notification)
            .where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
            .values(is_read=True)
        )
        await self.db.commit()
        return cast(CursorResult, result).rowcount > 0

    async def mark_all_read(self, user_id: uuid.UUID) -> int:
        """Mark all of a user's unread notifications as read.

        Returns the number of rows updated.
        """
        result = await self.db.execute(
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
            .values(is_read=True)
        )
        await self.db.commit()
        return cast(CursorResult, result).rowcount
