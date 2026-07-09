from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import ConsultationRecord, DraftSource, Reservation, ReservationStatus, User


class ReservationNotFound(Exception):
    pass


class NotAssignedCounselor(Exception):
    pass


class ReservationNotCompleted(Exception):
    pass


class RecordAlreadyExists(Exception):
    pass


def save_record(
    db: Session,
    reservation_id: int,
    counselor_user: User,
    *,
    raw_memo: str,
    summary: str | None,
    interested_products: list[str],
    recommendations: list[str],
    follow_up: str | None,
    purchase_linked: bool,
    draft_source: DraftSource,
) -> ConsultationRecord:
    """상담 기록 저장 — 배정 상담사만, 완료된 상담만, 예약당 1건 (§4.3-6)."""
    r = db.get(Reservation, reservation_id)
    if r is None:
        raise ReservationNotFound
    if r.slot.counselor.user_id != counselor_user.id:
        raise NotAssignedCounselor
    if r.status != ReservationStatus.completed:
        raise ReservationNotCompleted

    record = ConsultationRecord(
        reservation_id=reservation_id,
        raw_memo=raw_memo,
        summary=summary,
        interested_products=interested_products,
        recommendations=recommendations,
        follow_up=follow_up,
        purchase_linked=purchase_linked,
        draft_source=draft_source,
    )
    try:
        with db.begin_nested():
            db.add(record)
            db.flush()
    except IntegrityError as exc:
        raise RecordAlreadyExists from exc
    db.commit()
    return record


def get_record(db: Session, reservation_id: int) -> ConsultationRecord | None:
    return db.scalar(
        select(ConsultationRecord).where(
            ConsultationRecord.reservation_id == reservation_id
        )
    )
