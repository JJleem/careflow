import hashlib
import hmac
import re
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    ConsultationRecord,
    PurchaseEvent,
    Reservation,
    ReservationStatus,
    User,
)

ATTRIBUTION_WINDOW_DAYS = 30


def verify_signature(body: bytes, signature: str | None) -> bool:
    """HMAC-SHA256 서명 검증 — 시크릿을 아는 발신자만 유효한 웹훅을 만들 수 있다."""
    expected = hmac.new(
        get_settings().webhook_secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature or "")


def _normalize_phone(phone: str) -> str:
    return re.sub(r"\D", "", phone)


def ingest_purchase(
    db: Session,
    *,
    order_id: str,
    customer_phone: str,
    product_name: str,
    occurred_at: datetime,
) -> tuple[PurchaseEvent, bool]:
    """이벤트 적재 + 어트리뷰션. 반환: (이벤트, 신규 여부).

    멱등성(§4.7): order_id unique — 웹훅 재전송은 기존 이벤트를 그대로 반환.
    원본 이벤트가 남아 있어 매칭 규칙이 바뀌어도 재계산 가능 (§4.3-8).
    """
    event = PurchaseEvent(
        order_id=order_id,
        customer_phone=customer_phone,
        product_name=product_name,
        occurred_at=occurred_at,
    )
    try:
        with db.begin_nested():
            db.add(event)
            db.flush()
    except IntegrityError:
        existing = db.scalar(
            select(PurchaseEvent).where(PurchaseEvent.order_id == order_id)
        )
        return existing, False

    _attribute(db, event)
    db.commit()
    return event, True


def _attribute(db: Session, event: PurchaseEvent) -> None:
    """전화번호 일치 + 상담 완료 후 30일 윈도우. 후보 여러 건이면
    가장 최근 완료 상담 1건에만 연결 (이중 집계로 전환율 부풀림 방지, §4.7)."""
    phone = _normalize_phone(event.customer_phone)
    window_start = event.occurred_at - timedelta(days=ATTRIBUTION_WINDOW_DAYS)

    rows = db.execute(
        select(ConsultationRecord, Reservation, User)
        .join(Reservation, ConsultationRecord.reservation_id == Reservation.id)
        .join(User, Reservation.customer_id == User.id)
        .where(
            Reservation.status == ReservationStatus.completed,
            Reservation.completed_at.is_not(None),
            Reservation.completed_at <= event.occurred_at,
            Reservation.completed_at >= window_start,
        )
        .order_by(Reservation.completed_at.desc())
    ).all()

    for record, _reservation, customer in rows:
        if _normalize_phone(customer.phone) == phone:
            record.purchase_linked = True
            event.matched_record_id = record.id
            return
