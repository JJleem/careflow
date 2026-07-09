from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, pg_enum
from app.models.enums import BriefingStatus, DraftSource
from app.models.reservation import Reservation


class ConsultationRecord(CreatedAtMixin, Base):
    """상담 기록. raw_memo(원본)와 구조화 필드가 공존한다 (docs/04 §4.3-6).

    LLM 추출 초안은 상담사가 검수·수정 후 저장(휴먼 인 더 루프).
    draft_source로 LLM 사용 여부를 남겨 추출 품질을 사후 평가할 수 있다.
    """

    __tablename__ = "consultation_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    reservation_id: Mapped[int] = mapped_column(
        ForeignKey("reservations.id"), unique=True
    )
    raw_memo: Mapped[str] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    interested_products: Mapped[list[str]] = mapped_column(JSONB, default=list)
    recommendations: Mapped[list[str]] = mapped_column(JSONB, default=list)
    follow_up: Mapped[str | None] = mapped_column(Text)
    purchase_linked: Mapped[bool] = mapped_column(default=False)
    draft_source: Mapped[DraftSource] = mapped_column(
        pg_enum(DraftSource, "draft_source"), default=DraftSource.manual
    )

    reservation: Mapped[Reservation] = relationship()


class Briefing(CreatedAtMixin, Base):
    """LLM 사전 브리핑. 예약 생성 시 pending으로 만들어져 배치로 처리된다.

    참고 자료일 뿐이므로 failed여도 상담 플로우에 영향 없음 (NFR-3).
    """

    __tablename__ = "briefings"

    id: Mapped[int] = mapped_column(primary_key=True)
    reservation_id: Mapped[int] = mapped_column(
        ForeignKey("reservations.id"), unique=True
    )
    status: Mapped[BriefingStatus] = mapped_column(
        pg_enum(BriefingStatus, "briefing_status"), default=BriefingStatus.pending
    )
    content: Mapped[str | None] = mapped_column(Text)
    batch_id: Mapped[str | None] = mapped_column(String(100))

    reservation: Mapped[Reservation] = relationship()
