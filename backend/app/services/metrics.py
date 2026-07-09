from collections import Counter
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import ConsultationRecord, Reservation, ReservationStatus


def compute_metrics(db: Session, date_from: date, date_to: date) -> dict:
    """기간(KST 날짜, 양끝 포함) 내 상담 지표 (docs/04 §4.4 지표 정의).

    노쇼율 = no_show / (completed + no_show) — 진행됐어야 할 상담 대비
    전환율 = purchase_linked 기록 / completed — 어트리뷰션 결과 기반
    """
    kst = ZoneInfo(get_settings().timezone)
    start = datetime.combine(date_from, time.min, tzinfo=kst)
    end = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=kst)

    reservations = list(
        db.scalars(
            select(Reservation).where(
                Reservation.start_at >= start, Reservation.start_at < end
            )
        )
    )
    by_status = Counter(r.status for r in reservations)
    completed = by_status[ReservationStatus.completed]
    no_show = by_status[ReservationStatus.no_show]

    records = list(
        db.scalars(
            select(ConsultationRecord)
            .join(Reservation, ConsultationRecord.reservation_id == Reservation.id)
            .where(Reservation.start_at >= start, Reservation.start_at < end)
        )
    )
    purchase_linked = sum(1 for rec in records if rec.purchase_linked)
    product_counter: Counter[str] = Counter()
    for rec in records:
        product_counter.update(rec.interested_products)

    def _rate(numerator: int, denominator: int) -> float | None:
        return round(numerator / denominator, 4) if denominator else None

    return {
        "date_from": date_from,
        "date_to": date_to,
        "total_reservations": len(reservations),
        "completed": completed,
        "cancelled": by_status[ReservationStatus.cancelled],
        "no_show": no_show,
        "confirmed_upcoming": by_status[ReservationStatus.confirmed],
        "completion_rate": _rate(completed, len(reservations)),
        "no_show_rate": _rate(no_show, completed + no_show),
        "conversion_rate": _rate(purchase_linked, completed),
        "top_interested_products": [
            {"product": name, "count": cnt}
            for name, cnt in product_counter.most_common(5)
        ],
    }
