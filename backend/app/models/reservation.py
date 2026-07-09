from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Text, column, func, text
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, pg_enum
from app.models.enums import ReservationStatus
from app.models.slot import AvailabilitySlot
from app.models.test_result import TestResult
from app.models.user import Subject, User

# 슬롯을 점유하는 상태. cancelled만 제외 — partial unique index의 WHERE절과 동일해야 함
ACTIVE_STATUSES = (
    ReservationStatus.confirmed,
    ReservationStatus.completed,
    ReservationStatus.no_show,
)


class Reservation(CreatedAtMixin, Base):
    """예약. 이중 예약 차단은 앱 로직이 아닌 DB 제약으로 보장한다 (NFR-1, docs/04 §4.3-3).

    세 제약 모두 insert-first → 제약 위반 catch → 409 패턴으로 처리한다.
    "확인 후 삽입"은 확인과 삽입 사이 레이스를 막지 못하기 때문.
    """

    __tablename__ = "reservations"
    __table_args__ = (
        # 슬롯당 활성 예약 1건. cancelled는 제외되어 취소된 슬롯은 재예약 가능
        Index(
            "uq_active_reservation_per_slot",
            "slot_id",
            unique=True,
            postgresql_where=text(
                "status IN ('confirmed', 'completed', 'no_show')"
            ),
        ),
        # 동일 결과지당 진행 예정 예약 1건 (완료된 결과지 재상담은 허용)
        Index(
            "uq_confirmed_reservation_per_test_result",
            "test_result_id",
            unique=True,
            postgresql_where=text("status = 'confirmed'"),
        ),
        # 동일 고객의 시간 겹침 예약 차단. btree_gist 확장 필요 (마이그레이션에서 생성)
        ExcludeConstraint(
            (func.tstzrange(column("start_at"), column("end_at")), "&&"),
            (column("customer_id"), "="),
            using="gist",
            where=text("status = 'confirmed'"),
            name="ex_reservations_customer_time_overlap",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    slot_id: Mapped[int] = mapped_column(ForeignKey("availability_slots.id"))
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"))
    test_result_id: Mapped[int] = mapped_column(ForeignKey("test_results.id"))
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # 슬롯 시간의 복제본. EXCLUDE 제약이 동일 테이블 컬럼만 참조 가능해 예약 생성 시 복사
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[ReservationStatus] = mapped_column(
        pg_enum(ReservationStatus, "reservation_status"),
        default=ReservationStatus.confirmed,
    )
    pre_question: Mapped[str | None] = mapped_column(Text)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    slot: Mapped[AvailabilitySlot] = relationship()
    subject: Mapped[Subject] = relationship()
    test_result: Mapped[TestResult] = relationship()
    customer: Mapped[User] = relationship()
