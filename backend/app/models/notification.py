from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, pg_enum
from app.models.enums import NotificationType
from app.models.user import User


class Notification(CreatedAtMixin, Base):
    """인앱 알림. 리마인더는 발송 시점이 아니라 예약 생성 시
    scheduled_at이 박힌 행으로 미리 생성된다 (docs/04 §4.5).

    스케줄러는 scheduled_at <= now AND sent_at IS NULL만 폴링하면 되고,
    예약 취소 시 해당 행을 지우면 정합성이 맞는다.
    """

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    type: Mapped[NotificationType] = mapped_column(
        pg_enum(NotificationType, "notification_type")
    )
    message: Mapped[str] = mapped_column(Text)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    read: Mapped[bool] = mapped_column(default=False)

    user: Mapped[User] = relationship()
