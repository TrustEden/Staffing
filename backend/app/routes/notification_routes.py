from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app import models
from backend.app.database import get_db
from backend.app.dependencies import get_current_user
from backend.app.schemas import NotificationOut, NotificationUpdate
from backend.app.services.notification_service import NotificationService

router = APIRouter(tags=["notifications"])


def get_notification_service(db: Session = Depends(get_db)) -> NotificationService:
    return NotificationService(db)


@router.get("/", response_model=list[NotificationOut])
def list_notifications(
    unread_only: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> list[NotificationOut]:
    notifications = notification_service.list_notifications(current_user.id, unread_only=unread_only)
    return [NotificationOut.model_validate(notif) for notif in notifications]


@router.post("/{notification_id}/read", response_model=NotificationOut)
def update_notification(
    notification_id: UUID,
    payload: NotificationUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> NotificationOut:
    notification = db.get(models.Notification, notification_id)
    if not notification or notification.recipient_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    updated = notification_service.mark_read(notification_id, read=payload.read)
    return NotificationOut.model_validate(updated)


@router.post("/mark-all-read", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> None:
    notification_service.mark_all_read(current_user.id)
