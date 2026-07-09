"""APScheduler 잡 배선. 로직은 전부 서비스 레이어에 있고 여기는 호출만 —
별도 워커(Celery 등) 전환 시 이 파일만 교체한다 (docs/04 §4.1)."""

from apscheduler.schedulers.background import BackgroundScheduler

from app.adapters.notification_channel import InAppChannel
from app.db import SessionLocal
from app.services.notifications import dispatch_due_notifications, expire_past_waitlist

_channel = InAppChannel()


def _dispatch_job() -> None:
    with SessionLocal() as db:
        dispatch_due_notifications(db, _channel)


def _expire_waitlist_job() -> None:
    with SessionLocal() as db:
        expire_past_waitlist(db)


def create_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(_dispatch_job, "interval", seconds=60, id="dispatch_notifications")
    scheduler.add_job(_expire_waitlist_job, "interval", hours=1, id="expire_waitlist")
    return scheduler
