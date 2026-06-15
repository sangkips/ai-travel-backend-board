"""Notifications router – in-app alerts for place creators."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.dependencies import get_current_user, get_notification_service
from src.schemas.notifications import NotificationOut
from src.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get(
    "",
    response_model=list[NotificationOut],
    summary="Fetch in-app notifications",
)
async def list_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(50, le=200),
    current_user: dict = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> list[NotificationOut]:
    """Return notifications for the authenticated user.

    Poll this endpoint every 5 minutes to surface 'someone reviewed your place' alerts.
    """
    return await service.get_notifications(
        user_id=current_user["user_id"],
        unread_only=unread_only,
        limit=limit,
    )


@router.patch(
    "/{notification_id}/read",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Mark a notification as read",
)
async def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> None:
    """Mark a single notification as read."""
    updated = await service.mark_read(notification_id, current_user["user_id"])
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )


@router.patch(
    "/read-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Mark all notifications as read",
)
async def mark_all_read(
    current_user: dict = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> None:
    """Bulk-acknowledge all unread notifications for the current user."""
    await service.mark_all_read(current_user["user_id"])
