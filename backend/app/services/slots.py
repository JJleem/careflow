from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import ACTIVE_STATUSES, AvailabilitySlot, CounselorProfile, Reservation

SLOT_MINUTES = 30


class SlotNotFound(Exception):
    pass


class SlotHasActiveReservation(Exception):
    pass


def _kst() -> ZoneInfo:
    return ZoneInfo(get_settings().timezone)


def _day_bounds(day: date) -> tuple[datetime, datetime]:
    """KST 기준 하루를 UTC 경계로 변환 — 날짜 해석은 항상 Asia/Seoul (NFR-8)."""
    start = datetime.combine(day, time.min, tzinfo=_kst())
    return start, start + timedelta(days=1)


# 슬롯에 활성 예약이 붙어 있는가 (상관 서브쿼리)
_active_reservation_exists = exists().where(
    Reservation.slot_id == AvailabilitySlot.id,
    Reservation.status.in_(ACTIVE_STATUSES),
)


def get_counselor_profile(db: Session, user_id: int) -> CounselorProfile | None:
    return db.scalar(
        select(CounselorProfile).where(CounselorProfile.user_id == user_id)
    )


def list_my_slots(
    db: Session, counselor_id: int, date_from: date | None, date_to: date | None
) -> list[tuple[AvailabilitySlot, bool]]:
    stmt = (
        select(AvailabilitySlot, _active_reservation_exists.label("has_active"))
        .where(AvailabilitySlot.counselor_id == counselor_id)
        .order_by(AvailabilitySlot.start_at)
    )
    if date_from:
        stmt = stmt.where(AvailabilitySlot.start_at >= _day_bounds(date_from)[0])
    if date_to:
        stmt = stmt.where(AvailabilitySlot.start_at < _day_bounds(date_to)[1])
    return [(row[0], row[1]) for row in db.execute(stmt)]


def create_slot(
    db: Session, counselor_id: int, start_at: datetime
) -> AvailabilitySlot:
    """중복 시각 검사는 하지 않는다 — uq_counselor_start 위반을 라우터에서 409로 변환
    (insert-first 패턴, 예약과 동일한 원칙)."""
    slot = AvailabilitySlot(
        counselor_id=counselor_id,
        start_at=start_at,
        end_at=start_at + timedelta(minutes=SLOT_MINUTES),
    )
    db.add(slot)
    db.commit()
    return slot


def delete_slot(db: Session, counselor_id: int, slot_id: int) -> None:
    slot = db.scalar(
        select(AvailabilitySlot).where(
            AvailabilitySlot.id == slot_id,
            AvailabilitySlot.counselor_id == counselor_id,
        )
    )
    if slot is None:
        raise SlotNotFound
    # 활성 예약이 있는 슬롯 삭제 → 예약 고아화. 상담사 취소는 예약 전이로만 (docs/04 §4.7)
    has_active = db.scalar(
        select(
            exists().where(
                Reservation.slot_id == slot_id,
                Reservation.status.in_(ACTIVE_STATUSES),
            )
        )
    )
    if has_active:
        raise SlotHasActiveReservation
    db.delete(slot)
    db.commit()


def list_available_times(
    db: Session, day: date
) -> list[tuple[datetime, datetime, int]]:
    """시간대 기준 통합: 같은 시각의 빈 슬롯 수를 합산 (상담사는 노출하지 않음 — 자동 배정)."""
    day_start, day_end = _day_bounds(day)
    stmt = (
        select(
            AvailabilitySlot.start_at,
            AvailabilitySlot.end_at,
            func.count(AvailabilitySlot.id).label("available_count"),
        )
        .where(
            AvailabilitySlot.start_at >= day_start,
            AvailabilitySlot.start_at < day_end,
            AvailabilitySlot.start_at > datetime.now(timezone.utc),
            ~_active_reservation_exists,
        )
        .group_by(AvailabilitySlot.start_at, AvailabilitySlot.end_at)
        .order_by(AvailabilitySlot.start_at)
    )
    return [tuple(row) for row in db.execute(stmt)]


def find_alternative_dates(
    db: Session, day: date, scan_days: int = 7, limit: int = 3
) -> list[tuple[date, int]]:
    """요청일이 만석일 때 가까운 예약 가능 날짜 추천 (P3: 대안 없는 이탈 방지)."""
    alternatives = []
    for offset in range(1, scan_days + 1):
        candidate = day + timedelta(days=offset)
        times = list_available_times(db, candidate)
        if times:
            alternatives.append((candidate, len(times)))
        if len(alternatives) >= limit:
            break
    return alternatives
