from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin
from app.models.record import ConsultationRecord


class PurchaseEvent(CreatedAtMixin, Base):
    """구매 이벤트 원본. 기록에 바로 쓰지 않고 먼저 적재한 뒤 어트리뷰션
    (전화번호 일치 + 상담 완료 후 30일)으로 매칭한다 (docs/04 §4.3-8).

    order_id unique = 웹훅 재전송 멱등성 (§4.7). 원본이 남아 있어
    매칭 규칙이 바뀌어도 재계산 가능.
    """

    __tablename__ = "purchase_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[str] = mapped_column(String(100), unique=True)
    customer_phone: Mapped[str] = mapped_column(String(20))
    product_name: Mapped[str] = mapped_column(String(200))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    matched_record_id: Mapped[int | None] = mapped_column(
        ForeignKey("consultation_records.id")
    )

    matched_record: Mapped[ConsultationRecord | None] = relationship()
