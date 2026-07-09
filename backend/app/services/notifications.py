from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.notification_channel import NotificationChannel
from app.config import get_settings
from app.models import Notification, WaitlistEntry, WaitlistStatus


def dispatch_due_notifications(db: Session, channel: NotificationChannel) -> int:
    """scheduled_at이 지났고 아직 안 보낸 알림을 발송 (docs/04 §4.5 폴링 모델).

    발송 실패(False)면 sent_at을 남기지 않아 다음 폴링에서 자동 재시도된다.
    """
    now = datetime.now(timezone.utc)
    due = db.scalars(
        select(Notification).where(
            Notification.sent_at.is_(None),
            Notification.scheduled_at <= now,
        )
    )
    sent = 0
    for n in due:
        if channel.send(n):
            n.sent_at = now
            sent += 1
    db.commit()
    return sent


def expire_past_waitlist(db: Session) -> int:
    """희망일이 지난 대기 신청을 expired 처리 (§4.7 대기 만료)."""
    today = datetime.now(ZoneInfo(get_settings().timezone)).date()
    entries = db.scalars(
        select(WaitlistEntry).where(
            WaitlistEntry.status == WaitlistStatus.waiting,
            WaitlistEntry.desired_date < today,
        )
    )
    count = 0
    for e in entries:
        e.status = WaitlistStatus.expired
        count += 1
    db.commit()
    return count


def list_my_notifications(
    db: Session, user_id: int, limit: int = 50
) -> list[Notification]:
    """알림함: 발송 시점이 도래한 것만 노출 (미래 리마인더는 아직 안 보임)."""
    now = datetime.now(timezone.utc)
    return list(
        db.scalars(
            select(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.scheduled_at <= now,
            )
            .order_by(Notification.scheduled_at.desc())
            .limit(limit)
        )
    )


def mark_read(db: Session, user_id: int, notification_id: int) -> Notification | None:
    n = db.get(Notification, notification_id)
    if n is None or n.user_id != user_id:
        return None
    n.read = True
    db.commit()
    return n
