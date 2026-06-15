"""Notification service – fetch and acknowledge in-app alerts."""

import uuid

from src.repositories.notification_repository import NotificationRepository
from src.schemas.notifications import NotificationOut


class NotificationService:
    """Handles in-app notification retrieval and read-state management."""

    def __init__(self, notification_repo: NotificationRepository) -> None:
        self._notifications = notification_repo

    async def get_notifications(
        self,
        user_id: uuid.UUID,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[NotificationOut]:
        """Return notifications for the authenticated user.

        Mobile client polls this every 5 minutes (MVP).
        """
        notifs = await self._notifications.get_for_user(user_id, unread_only=unread_only, limit=limit)
        return [self._to_out(n) for n in notifs]

    async def mark_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Mark a single notification as read.

        Returns False if the notification was not found or belongs to a different user.
        """
        return await self._notifications.mark_read(notification_id, user_id)

    async def mark_all_read(self, user_id: uuid.UUID) -> int:
        """Mark all of a user's notifications as read. Returns count updated."""
        return await self._notifications.mark_all_read(user_id)

    @staticmethod
    def _to_out(notif) -> NotificationOut:
        return NotificationOut(
            id=notif.id,
            place_id=notif.place_id,
            place_name=notif.place.name if notif.place else None,
            review_id=notif.review_id,
            reviewer_role=(notif.review.role_at_time if notif.review else None),
            is_read=notif.is_read,
            created_at=notif.created_at,
        )
