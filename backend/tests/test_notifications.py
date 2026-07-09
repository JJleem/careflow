"""알림 발송·대기 만료·알림함 검증 — 리마인더 폴링 모델(docs/04 §4.5)과
채널 어댑터 계약(실패 시 재시도, NFR-4)."""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from app.adapters.notification_channel import InAppChannel, NotificationChannel
from app.models import (
    Notification,
    NotificationType,
    WaitlistEntry,
    WaitlistStatus,
)
from app.security import create_access_token
from app.services.notifications import (
    dispatch_due_notifications,
    expire_past_waitlist,
    list_my_notifications,
)
from tests.test_reservations import make_world

NOW = datetime.now(timezone.utc)


class FailingChannel(NotificationChannel):
    def send(self, notification):
        return False


def _notif(user_id, minutes_offset, ntype=NotificationType.reminder_24h):
    return Notification(
        user_id=user_id,
        type=ntype,
        message="테스트 알림",
        scheduled_at=NOW + timedelta(minutes=minutes_offset),
    )


def test_dispatch_sends_due_only(db):
    """지난 알림만 발송, 미래 리마인더는 대기."""
    w = make_world(db)
    due = _notif(w.customers[0].id, -5)
    future = _notif(w.customers[0].id, +60)
    db.add_all([due, future])
    db.commit()

    sent = dispatch_due_notifications(db, InAppChannel())

    assert sent == 1
    assert due.sent_at is not None
    assert future.sent_at is None


def test_failed_send_retries_next_poll(db):
    """채널 실패(False) 시 sent_at 미기록 → 다음 폴링에서 재시도 (어댑터 계약)."""
    w = make_world(db)
    n = _notif(w.customers[0].id, -5)
    db.add(n)
    db.commit()

    assert dispatch_due_notifications(db, FailingChannel()) == 0
    assert n.sent_at is None
    # 채널 복구 후 재시도 성공
    assert dispatch_due_notifications(db, InAppChannel()) == 1
    assert n.sent_at is not None


def test_expire_past_waitlist(db):
    """희망일 경과 대기만 expired, 오늘·미래 대기는 유지 (§4.7)."""
    w = make_world(db)
    past = WaitlistEntry(
        customer_id=w.customers[0].id,
        desired_date=date.today() - timedelta(days=1),
        status=WaitlistStatus.waiting,
    )
    upcoming = WaitlistEntry(
        customer_id=w.customers[0].id,
        desired_date=date.today() + timedelta(days=3),
        status=WaitlistStatus.waiting,
    )
    db.add_all([past, upcoming])
    db.commit()

    assert expire_past_waitlist(db) == 1
    assert past.status == WaitlistStatus.expired
    assert upcoming.status == WaitlistStatus.waiting


def test_inbox_hides_future_reminders(db):
    """알림함에는 발송 시점이 도래한 것만 — 미래 리마인더 미노출."""
    w = make_world(db)
    db.add_all([_notif(w.customers[0].id, -10), _notif(w.customers[0].id, +30)])
    db.commit()

    inbox = list_my_notifications(db, w.customers[0].id)
    assert len(inbox) == 1


def test_mark_read_own_only(client, db):
    """읽음 처리는 본인 알림만 — 타인 알림은 404 (존재 여부도 비노출)."""
    w = make_world(db)
    n = _notif(w.customers[0].id, -5)
    db.add(n)
    db.commit()

    owner = {"Authorization": f"Bearer {create_access_token(w.customers[0].id, 'customer')}"}
    other = {"Authorization": f"Bearer {create_access_token(w.customers[1].id, 'customer')}"}

    assert client.patch(f"/notifications/{n.id}/read", headers=other).status_code == 404
    res = client.patch(f"/notifications/{n.id}/read", headers=owner)
    assert res.status_code == 200
    assert res.json()["read"] is True
