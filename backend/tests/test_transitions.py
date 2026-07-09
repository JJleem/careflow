"""상태 전이 검증 — docs/04 §4.10 테스트 전략 2·3번:
전이 규칙(시점 가드, 종결 상태 불변)과 취소 사이드이펙트(대기자 알림 포함)."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.models import (
    AvailabilitySlot,
    Briefing,
    BriefingStatus,
    Notification,
    NotificationType,
    Reservation,
    ReservationStatus,
    WaitlistEntry,
    WaitlistStatus,
)
from app.services.reservations import (
    InvalidTransition,
    PermissionDenied,
    create_reservation,
    transition_reservation,
)
from tests.test_reservations import T, make_world

KST = ZoneInfo("Asia/Seoul")


def make_past_reservation(db, w, hours_ago: int = 1) -> Reservation:
    """시점 가드 테스트용: 이미 시작된 confirmed 예약 (서비스 우회 직접 생성)."""
    start = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    slot = AvailabilitySlot(
        counselor_id=w.profiles[0].id, start_at=start,
        end_at=start + timedelta(minutes=30),
    )
    db.add(slot)
    db.flush()
    r = Reservation(
        slot_id=slot.id, subject_id=w.subjects[0].id,
        test_result_id=w.results[0].id, customer_id=w.customers[0].id,
        start_at=slot.start_at, end_at=slot.end_at,
        status=ReservationStatus.confirmed, confirmed_at=start,
    )
    db.add(r)
    db.commit()
    return r


def test_cancel_runs_all_side_effects(db):
    """취소 한 번에: 리마인더 삭제 + 브리핑 취소 + 취소 알림 + 대기자 알림."""
    w = make_world(db)
    r = create_reservation(db, w.customers[0].id, w.subjects[0].id, w.results[0].id, T)
    waiter = WaitlistEntry(
        customer_id=w.customers[1].id,
        desired_date=T.astimezone(KST).date(),
        status=WaitlistStatus.waiting,
    )
    db.add(waiter)
    db.commit()

    transition_reservation(db, r.id, ReservationStatus.cancelled, actor=w.customers[0])

    assert r.status == ReservationStatus.cancelled
    assert r.cancelled_at is not None
    # 이 예약의 미발송 리마인더는 삭제, 확정 알림(이력)은 보존
    remaining = {
        n.type for n in db.scalars(
            select(Notification).where(Notification.reservation_id == r.id)
        )
    }
    assert NotificationType.reminder_24h not in remaining
    assert NotificationType.reminder_1h not in remaining
    assert NotificationType.confirm in remaining
    assert NotificationType.cancel in remaining
    # pending 브리핑 → cancelled
    briefing = db.scalar(select(Briefing).where(Briefing.reservation_id == r.id))
    assert briefing.status == BriefingStatus.cancelled
    # 대기자: notified 전환 + waitlist 알림 수신
    db.refresh(waiter)
    assert waiter.status == WaitlistStatus.notified
    waitlist_notif = db.scalar(
        select(Notification).where(
            Notification.user_id == w.customers[1].id,
            Notification.type == NotificationType.waitlist,
        )
    )
    assert waitlist_notif is not None


def test_cancel_preserves_other_reservation_reminders(db):
    """같은 고객의 다른 예약 리마인더는 건드리지 않는다 (reservation_id 연결의 이유)."""
    w = make_world(db, counselors=2)
    r1 = create_reservation(db, w.customers[0].id, w.subjects[0].id, w.results[0].id, T)
    slot2 = AvailabilitySlot(
        counselor_id=w.profiles[0].id, start_at=T + timedelta(hours=2),
        end_at=T + timedelta(hours=2, minutes=30),
    )
    db.add(slot2)
    db.commit()
    r2 = create_reservation(
        db, w.customers[0].id, w.subjects[0].id, w.results[2].id,
        T + timedelta(hours=2),
    )

    transition_reservation(db, r1.id, ReservationStatus.cancelled, actor=w.customers[0])

    r2_reminders = list(db.scalars(
        select(Notification).where(
            Notification.reservation_id == r2.id,
            Notification.type.in_(
                (NotificationType.reminder_24h, NotificationType.reminder_1h)
            ),
        )
    ))
    assert len(r2_reminders) == 2  # 그대로 살아 있어야 함


def test_cancel_after_start_blocked(db):
    w = make_world(db)
    r = make_past_reservation(db, w)
    try:
        transition_reservation(db, r.id, ReservationStatus.cancelled, actor=w.customers[0])
        raise AssertionError("차단되어야 한다")
    except InvalidTransition as e:
        assert "시작 후" in e.reason


def test_complete_before_start_blocked(db):
    w = make_world(db)
    r = create_reservation(db, w.customers[0].id, w.subjects[0].id, w.results[0].id, T)
    try:
        transition_reservation(db, r.id, ReservationStatus.completed, actor=w.counselors[0])
        raise AssertionError("차단되어야 한다")
    except InvalidTransition as e:
        assert "시작 전" in e.reason


def test_complete_and_no_show_after_start(db):
    w = make_world(db)
    r1 = make_past_reservation(db, w, hours_ago=2)
    done = transition_reservation(
        db, r1.id, ReservationStatus.completed, actor=w.counselors[0]
    )
    assert done.status == ReservationStatus.completed
    assert done.completed_at is not None

    # 별도 예약으로 노쇼 (같은 결과지 confirmed 중복은 completed면 허용되므로 새 결과지 불필요)
    w2_slot_time = datetime.now(timezone.utc) - timedelta(hours=1)
    slot = AvailabilitySlot(
        counselor_id=w.profiles[0].id, start_at=w2_slot_time,
        end_at=w2_slot_time + timedelta(minutes=30),
    )
    db.add(slot)
    db.flush()
    r2 = Reservation(
        slot_id=slot.id, subject_id=w.subjects[1].id,
        test_result_id=w.results[1].id, customer_id=w.customers[1].id,
        start_at=slot.start_at, end_at=slot.end_at,
        status=ReservationStatus.confirmed,
    )
    db.add(r2)
    db.commit()
    noshow = transition_reservation(
        db, r2.id, ReservationStatus.no_show, actor=w.counselors[0]
    )
    assert noshow.status == ReservationStatus.no_show
    assert noshow.no_show_at is not None


def test_terminal_state_is_immutable(db):
    """completed → cancelled 불가 (§4.10-2)."""
    w = make_world(db)
    r = make_past_reservation(db, w)
    transition_reservation(db, r.id, ReservationStatus.completed, actor=w.counselors[0])
    try:
        transition_reservation(db, r.id, ReservationStatus.cancelled, actor=w.counselors[0])
        raise AssertionError("차단되어야 한다")
    except InvalidTransition as e:
        assert "completed" in e.reason


def test_access_control(db):
    """타인 예약 취소 불가, 고객의 완료 처리 불가, 미배정 상담사 처리 불가."""
    w = make_world(db, counselors=2)
    r = make_past_reservation(db, w)

    for actor, target in (
        (w.customers[1], ReservationStatus.cancelled),   # 남의 예약
        (w.customers[0], ReservationStatus.completed),   # 고객은 완료 불가
        (w.counselors[1], ReservationStatus.completed),  # 배정 안 된 상담사
    ):
        try:
            transition_reservation(db, r.id, target, actor=actor)
            raise AssertionError("차단되어야 한다")
        except PermissionDenied:
            pass
