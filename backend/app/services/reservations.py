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
    BriefingStatus,
    Notification,
    NotificationType,
    Reservation,
    ReservationStatus,
    Subject,
    TestResult,
    User,
    UserRole,
    WaitlistEntry,
    WaitlistStatus,
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
            reservation_id=r.id,
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
                    reservation_id=r.id,
                    type=ntype,
                    message=f"{label} {when} 상담이 예정되어 있습니다.",
                    scheduled_at=at,
                )
            )
    db.add(Briefing(reservation_id=r.id))


class ReservationNotFound(Exception):
    pass


class PermissionDenied(Exception):
    pass


class InvalidTransition(Exception):
    def __init__(self, reason: str):
        self.reason = reason


def transition_reservation(
    db: Session,
    reservation_id: int,
    target: ReservationStatus,
    actor: User,
) -> Reservation:
    """모든 상태 전이의 유일한 통로 (docs/04 §4.4). API·스케줄러 어디서 부르든
    인가·시점 가드·사이드이펙트가 동일하게 적용된다."""
    r = db.get(Reservation, reservation_id)
    if r is None:
        raise ReservationNotFound

    if actor.role == UserRole.customer:
        if r.customer_id != actor.id:
            raise PermissionDenied
        if target != ReservationStatus.cancelled:
            raise PermissionDenied  # 고객은 취소만 가능
    elif actor.role == UserRole.counselor:
        if r.slot.counselor.user_id != actor.id:
            raise PermissionDenied  # 배정 상담사만
    else:
        raise PermissionDenied

    if r.status != ReservationStatus.confirmed:
        raise InvalidTransition(f"'{r.status}' 상태에서는 전이할 수 없습니다")

    now = datetime.now(timezone.utc)
    # 시점 가드 (§4.7): 취소=시작 전, 완료/노쇼=시작 후 — 지표 오염 방지
    if target == ReservationStatus.cancelled and now >= r.start_at:
        raise InvalidTransition("상담 시작 후에는 취소할 수 없습니다")
    if target in (ReservationStatus.completed, ReservationStatus.no_show):
        if now < r.start_at:
            raise InvalidTransition("상담 시작 전에는 완료/노쇼 처리할 수 없습니다")

    r.status = target
    if target == ReservationStatus.cancelled:
        r.cancelled_at = now
        _on_cancel(db, r, by_counselor=actor.role == UserRole.counselor)
    elif target == ReservationStatus.completed:
        r.completed_at = now
    elif target == ReservationStatus.no_show:
        r.no_show_at = now

    db.commit()
    return r


def _on_cancel(db: Session, r: Reservation, by_counselor: bool) -> None:
    """취소의 사이드이펙트 4종 — 전이와 같은 트랜잭션 (§4.4).
    슬롯 해제는 별도 처리 불필요: cancelled는 partial unique index에서 빠지므로
    상태 변경 자체가 곧 슬롯 해제다."""
    now = datetime.now(timezone.utc)
    kst = ZoneInfo(get_settings().timezone)
    when = r.start_at.astimezone(kst).strftime("%m월 %d일 %H:%M")

    # 1. 이 예약의 미발송 리마인더 삭제
    for n in db.scalars(
        select(Notification).where(
            Notification.reservation_id == r.id,
            Notification.sent_at.is_(None),
            Notification.type.in_(
                (NotificationType.reminder_24h, NotificationType.reminder_1h)
            ),
        )
    ):
        db.delete(n)

    # 2. pending 브리핑 취소 (LLM 비용 낭비 차단, §4.7)
    briefing = db.scalar(select(Briefing).where(Briefing.reservation_id == r.id))
    if briefing is not None and briefing.status == BriefingStatus.pending:
        briefing.status = BriefingStatus.cancelled

    # 3. 고객에게 취소 확인 알림 (상담사 취소면 재예약 유도)
    message = (
        f"상담사 사정으로 {when} 상담이 취소되었습니다. 다른 시간대로 다시 예약해 주세요."
        if by_counselor
        else f"{when} 상담 예약이 취소되었습니다."
    )
    db.add(
        Notification(
            user_id=r.customer_id,
            reservation_id=r.id,
            type=NotificationType.cancel,
            message=message,
            scheduled_at=now,
        )
    )

    # 4. 해당 날짜 대기자 전원 알림 → 선착순 재예약 (§4.7)
    cancelled_date = r.start_at.astimezone(kst).date()
    for entry in db.scalars(
        select(WaitlistEntry).where(
            WaitlistEntry.desired_date == cancelled_date,
            WaitlistEntry.status == WaitlistStatus.waiting,
        )
    ):
        entry.status = WaitlistStatus.notified
        db.add(
            Notification(
                user_id=entry.customer_id,
                type=NotificationType.waitlist,
                message=f"{cancelled_date:%m월 %d일}에 상담 자리가 생겼습니다. 지금 예약해 보세요.",
                scheduled_at=now,
            )
        )


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
