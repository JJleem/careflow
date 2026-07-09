"""예약 코어 검증 — docs/04 §4.10 테스트 전략 1번:
동시 예약 2건 → 정확히 1건 성공. 슬롯 unique와 고객 시간겹침 EXCLUDE 모두."""

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy import func, select

from app.models import (
    ACTIVE_STATUSES,
    AvailabilitySlot,
    Briefing,
    CounselorProfile,
    Notification,
    Reservation,
    ReservationStatus,
    ServiceType,
    Subject,
    SubjectRelation,
    TestResult,
    User,
    UserRole,
)
from app.services.reservations import (
    DuplicateReservation,
    NoAvailableSlot,
    create_reservation,
)

T = datetime.now(timezone.utc).replace(
    minute=0, second=0, microsecond=0
) + timedelta(days=2)


def make_world(db, counselors=1):
    """고객 2명(피검자·결과지 각 1, 고객1은 결과지 2), 상담사 N명(시각 T 슬롯 각 1)."""
    users = [
        User(email=f"cu{i}@t.kr", password_hash="x", role=UserRole.customer,
             name=f"고객{i}", phone=f"010-0000-000{i}")
        for i in (1, 2)
    ]
    counselor_users = [
        User(email=f"co{i}@t.kr", password_hash="x", role=UserRole.counselor,
             name=f"상담사{i}", phone=f"010-9999-000{i}")
        for i in range(1, counselors + 1)
    ]
    db.add_all(users + counselor_users)
    db.flush()

    profiles = [CounselorProfile(user_id=u.id) for u in counselor_users]
    subjects = [
        Subject(owner_user_id=u.id, name=u.name, birth_date=date(1990, 1, 1),
                relation=SubjectRelation.self)
        for u in users
    ]
    db.add_all(profiles + subjects)
    db.flush()

    results = [
        TestResult(subject_id=s.id, service_type=ServiceType.comprehensive_metabolic,
                   reported_at=date(2026, 7, 1), indicators=[])
        for s in subjects
    ]
    results.append(
        TestResult(subject_id=subjects[0].id, service_type=ServiceType.heavy_metal,
                   reported_at=date(2026, 7, 1), indicators=[])
    )
    slots = [
        AvailabilitySlot(counselor_id=p.id, start_at=T,
                         end_at=T + timedelta(minutes=30))
        for p in profiles
    ]
    db.add_all(results + slots)
    db.commit()
    return SimpleNamespace(
        customers=users, counselors=counselor_users, profiles=profiles,
        subjects=subjects, results=results, slots=slots,
    )


def active_count(db):
    return db.scalar(
        select(func.count()).select_from(Reservation).where(
            Reservation.status.in_(ACTIVE_STATUSES)
        )
    )


def test_concurrent_same_slot_exactly_one_succeeds(session_factory):
    """NFR-1의 증명: 마지막 슬롯 1개에 두 고객이 동시 예약 → 정확히 1건만 성공."""
    setup = session_factory()
    w = make_world(setup, counselors=1)
    args = [
        (w.customers[0].id, w.subjects[0].id, w.results[0].id),
        (w.customers[1].id, w.subjects[1].id, w.results[1].id),
    ]
    setup.close()

    barrier = threading.Barrier(2)

    def attempt(customer_id, subject_id, result_id):
        db = session_factory()
        try:
            barrier.wait()  # 두 스레드가 정확히 같은 순간 INSERT에 돌입
            create_reservation(db, customer_id, subject_id, result_id, T)
            return "ok"
        except NoAvailableSlot:
            return "full"
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = sorted(pool.map(lambda a: attempt(*a), args))

    assert outcomes == ["full", "ok"]
    check = session_factory()
    assert active_count(check) == 1
    check.close()


def test_concurrent_retry_assigns_second_counselor(session_factory):
    """동시 충돌 시 차순위 상담사로 재시도 → 둘 다 성공하되 서로 다른 슬롯 (§4.5)."""
    setup = session_factory()
    w = make_world(setup, counselors=2)
    args = [
        (w.customers[0].id, w.subjects[0].id, w.results[0].id),
        (w.customers[1].id, w.subjects[1].id, w.results[1].id),
    ]
    setup.close()

    barrier = threading.Barrier(2)

    def attempt(customer_id, subject_id, result_id):
        db = session_factory()
        try:
            barrier.wait()
            return create_reservation(db, customer_id, subject_id, result_id, T).slot_id
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        slot_ids = list(pool.map(lambda a: attempt(*a), args))

    assert len(set(slot_ids)) == 2  # 서로 다른 슬롯에 배정
    check = session_factory()
    assert active_count(check) == 2
    check.close()


def test_customer_time_overlap_blocked(db, session_factory):
    """같은 고객이 같은 시각에 두 번째 예약 → GiST EXCLUDE가 차단."""
    w = make_world(db, counselors=2)
    create_reservation(db, w.customers[0].id, w.subjects[0].id, w.results[0].id, T)
    try:
        create_reservation(db, w.customers[0].id, w.subjects[0].id, w.results[2].id, T)
        raise AssertionError("차단되어야 한다")
    except DuplicateReservation as e:
        assert "시간대" in e.reason


def test_same_test_result_blocked(db):
    """같은 결과지로 진행 예정 예약이 이미 있으면 차단 (다른 시각이어도)."""
    w = make_world(db, counselors=1)
    create_reservation(db, w.customers[0].id, w.subjects[0].id, w.results[0].id, T)
    db.add(AvailabilitySlot(counselor_id=w.slots[0].counselor_id,
                            start_at=T + timedelta(hours=2),
                            end_at=T + timedelta(hours=2, minutes=30)))
    db.commit()
    try:
        create_reservation(db, w.customers[0].id, w.subjects[0].id, w.results[0].id,
                           T + timedelta(hours=2))
        raise AssertionError("차단되어야 한다")
    except DuplicateReservation as e:
        assert "결과지" in e.reason


def test_cancelled_slot_is_rebookable(db):
    """취소된 예약의 슬롯은 재예약 가능 — partial unique index의 존재 이유."""
    w = make_world(db, counselors=1)
    first = create_reservation(db, w.customers[0].id, w.subjects[0].id,
                               w.results[0].id, T)
    first.status = ReservationStatus.cancelled
    db.commit()

    second = create_reservation(db, w.customers[1].id, w.subjects[1].id,
                                w.results[1].id, T)
    assert second.slot_id == first.slot_id
    assert active_count(db) == 1


def test_side_effects_created_in_same_transaction(db):
    """예약 생성 시 확정 알림 1 + 리마인더 2 + 브리핑(pending) 1이 함께 생긴다."""
    w = make_world(db, counselors=1)
    r = create_reservation(db, w.customers[0].id, w.subjects[0].id, w.results[0].id, T)

    notif_count = db.scalar(
        select(func.count()).select_from(Notification).where(
            Notification.user_id == w.customers[0].id
        )
    )
    assert notif_count == 3  # confirm + reminder_24h + reminder_1h (T는 48시간 뒤)
    briefing = db.scalar(select(Briefing).where(Briefing.reservation_id == r.id))
    assert briefing is not None and briefing.status.value == "pending"
