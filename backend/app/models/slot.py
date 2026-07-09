from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin
from app.models.user import CounselorProfile


class AvailabilitySlot(CreatedAtMixin, Base):
    """상담사의 시간 공급. 슬롯을 행으로 미리 생성해 두므로
    가용 조회가 단순 SELECT, 이중 예약 차단이 유니크 제약으로 환원된다 (docs/04 §4.3-2)."""

    __tablename__ = "availability_slots"
    __table_args__ = (
        UniqueConstraint("counselor_id", "start_at", name="uq_counselor_start"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    counselor_id: Mapped[int] = mapped_column(ForeignKey("counselor_profiles.id"))
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    counselor: Mapped[CounselorProfile] = relationship()
