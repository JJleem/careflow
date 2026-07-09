from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import NotificationType


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: NotificationType
    message: str
    scheduled_at: datetime
    read: bool
