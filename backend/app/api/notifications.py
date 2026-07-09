from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import get_db
from app.models import User
from app.schemas.notification import NotificationResponse
from app.services import notifications as notification_service

router = APIRouter(prefix="/notifications", tags=["알림"])

DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("")
def my_notifications(user: CurrentUser, db: DB) -> list[NotificationResponse]:
    return [
        NotificationResponse.model_validate(n)
        for n in notification_service.list_my_notifications(db, user.id)
    ]


@router.patch("/{notification_id}/read")
def mark_read(
    user: CurrentUser, db: DB, notification_id: int
) -> NotificationResponse:
    n = notification_service.mark_read(db, user.id, notification_id)
    if n is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="알림이 없습니다")
    return NotificationResponse.model_validate(n)
