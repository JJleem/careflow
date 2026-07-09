from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    ACTIVE_STATUSES,
    AvailabilitySlot,
    Briefing,
    Notification,
    NotificationType,
    Reservation,
    ReservationStatus,
    Subject,
    TestResult,
)


class SubjectNotOwned(Exception):
    pass


class TestResultNotFound(Exception):
    pass


class InvalidStartTime(Exception):
    pass


class NoAvailableSlot(Exception):
    """해당 시각 전 슬롯 만석 (동시 선점으로 인한 재시도 소진 포함)."""


class DuplicateReservation(Exception):
    def __init__(self, reason: str):
        self.reason = reason


_SLOT_TAKEN = "uq_active_reservation_per_slot"
_RESULT_DUP = "uq_confirmed_reservation_per_test_result"
_TIME_OVERLAP = "ex_reservations_customer_time_overlap"


def _violated_constraint(exc: IntegrityError) -> str:
    diag = getattr(exc.orig, "diag", None)
    return getattr(diag, "constraint_name", None) or ""


def _candidate_slots(
    db: Session, start_at: datetime, subject_id: int
) -> list[AvailabilitySlot]:
    """해당 시각 빈 슬롯을 배정 우선순위로 정렬 (docs/04 §4.7 하이브리드 배정).

    1순위: 이 피검자의 마지막 완료 상담 상담사 (재상담 맥락 연속성)
    2순위: 진행 예정(confirmed) 예약이 적은 상담사 (부하 균등)
    """
    free = ~exists().where(
        Reservation.slot_id == AvailabilitySlot.id,
        Reservation.status.in_(ACTIVE_STATUSES),
    )
    slots = list(
        db.scalars(
            select(AvailabilitySlot).where(
                AvailabilitySlot.start_at == start_at, free
            )
        )
    )
    if not slots:
        return []

    prev_counselor_id = db.scalar(
        select(AvailabilitySlot.counselor_id)
        .join(Reservation, Reservation.slot_id == AvailabilitySlot.id)
        .where(
            Reservation.subject_id == subject_id,
            Reservation.status == ReservationStatus.completed,
        )
        .order_by(Reservation.start_at.desc())
        .limit(1)
    )
    loads = dict(
        db.execute(
            select(AvailabilitySlot.counselor_id, func.count(Reservation.id))
            .join(Reservation, Reservation.slot_id == AvailabilitySlot.id)
            .where(Reservation.status == ReservationStatus.confirmed)
            .group_by(AvailabilitySlot.counselor_id)
        ).all()
    )
    slots.sort(
        key=lambda s: (
            s.counselor_id != prev_counselor_id,
            loads.get(s.counselor_id, 0),
        )
    )
    return slots


def create_reservation(
    db: Session,
    customer_id: int,
    subject_id: int,
    test_result_id: int,
    start_at: datetime,
    pre_question: str | None = None,
) -> Reservation:
    subject = db.get(Subject, subject_id)
    if subject is None or subject.owner_user_id != customer_id:
        raise SubjectNotOwned
    result = db.get(TestResult, test_result_id)
    if result is None or result.subject_id != subject_id:
        raise TestResultNotFound
    if start_at <= datetime.now(timezone.utc):
        raise InvalidStartTime

    for slot in _candidate_slots(db, start_at, subject_id):
        reservation = Reservation(
            slot_id=slot.id,
            subject_id=subject_id,
            test_result_id=test_result_id,
            customer_id=customer_id,
            start_at=slot.start_at,
            end_at=slot.end_at,
            status=ReservationStatus.confirmed,
            pre_question=pre_question,
            confirmed_at=datetime.now(timezone.utc),
        )
        try:
            # savepoint: 제약 위반이 나도 트랜잭션 전체가 죽지 않고 다음 후보 재시도 가능
            with db.begin_nested():
                db.add(reservation)
                db.flush()
        except IntegrityError as exc:
            name = _violated_constraint(exc)
            if name == _SLOT_TAKEN:
                continue  # 동시 요청이 먼저 선점 — 같은 시각 차순위 상담사로 (§4.5)
            if name == _RESULT_DUP:
                raise DuplicateReservation(
                    "이 결과지에 이미 진행 예정인 예약이 있습니다"
                ) from exc
            if name == _TIME_OVERLAP:
                raise DuplicateReservation(
                    "같은 시간대에 이미 다른 상담 예약이 있습니다"
                ) from exc
            raise
        else:
            _create_side_effects(db, reservation)
            db.commit()
            return reservation

    raise NoAvailableSlot


def _create_side_effects(db: Session, r: Reservation) -> None:
    """확정 알림 + 리마인더 + 브리핑. 예약 INSERT와 같은 트랜잭션이어야
    '예약은 됐는데 알림이 없는' 어긋난 상태가 불가능하다."""
    kst = ZoneInfo(get_settings().timezone)
    when = r.start_at.astimezone(kst).strftime("%m월 %d일 %H:%M")
    now = datetime.now(timezone.utc)

    db.add(
        Notification(
            user_id=r.customer_id,
            type=NotificationType.confirm,
            message=f"{when} 상담 예약이 확정되었습니다.",
            scheduled_at=now,
        )
    )
    reminders = (
        (timedelta(hours=24), NotificationType.reminder_24h, "내일"),
        (timedelta(hours=1), NotificationType.reminder_1h, "1시간 뒤"),
    )
    for delta, ntype, label in reminders:
        at = r.start_at - delta
        if at > now:  # 임박 예약: 이미 지난 시점의 리마인더는 생성하지 않음 (§4.7)
            db.add(
                Notification(
                    user_id=r.customer_id,
                    type=ntype,
                    message=f"{label} {when} 상담이 예정되어 있습니다.",
                    scheduled_at=at,
                )
            )
    db.add(Briefing(reservation_id=r.id))


def list_my_reservations_as_customer(
    db: Session, customer_id: int
) -> list[Reservation]:
    return list(
        db.scalars(
            select(Reservation)
            .where(Reservation.customer_id == customer_id)
            .order_by(Reservation.start_at.desc())
        )
    )


def list_my_reservations_as_counselor(
    db: Session, counselor_id: int
) -> list[Reservation]:
    return list(
        db.scalars(
            select(Reservation)
            .join(AvailabilitySlot, Reservation.slot_id == AvailabilitySlot.id)
            .where(AvailabilitySlot.counselor_id == counselor_id)
            .order_by(Reservation.start_at.desc())
        )
    )
