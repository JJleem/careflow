from datetime import date
from typing import Any

from sqlalchemy import Date, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, pg_enum
from app.models.enums import ServiceType
from app.models.user import Subject


class TestResult(CreatedAtMixin, Base):
    """검사 결과지. 지표는 서비스마다 구성이 달라 JSONB (docs/04 §4.3-5).

    indicators 형태: [{"name": ..., "value": ..., "unit": ..., "range": ..., "comment": ...}]
    """

    __tablename__ = "test_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"))
    service_type: Mapped[ServiceType] = mapped_column(
        pg_enum(ServiceType, "service_type")
    )
    reported_at: Mapped[date] = mapped_column(Date)
    indicators: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)

    subject: Mapped[Subject] = relationship()
