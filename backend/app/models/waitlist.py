from datetime import date

from sqlalchemy import Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, pg_enum
from app.models.enums import WaitlistStatus
from app.models.user import User


class WaitlistEntry(CreatedAtMixin, Base):
    """만석 시 대기 신청. 날짜 단위이며, 취소 발생 시 해당 날짜 대기자 전원에게
    알림 → 선착순 재예약 (docs/04 §4.7). 홀드 없음 — 이중 예약은 DB 제약이 차단."""

    __tablename__ = "waitlist_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    desired_date: Mapped[date] = mapped_column(Date)
    status: Mapped[WaitlistStatus] = mapped_column(
        pg_enum(WaitlistStatus, "waitlist_status"), default=WaitlistStatus.waiting
    )

    customer: Mapped[User] = relationship()
