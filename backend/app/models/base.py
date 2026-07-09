from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


def pg_enum(enum_cls: type[StrEnum], name: str) -> Enum:
    """PostgreSQL native enum 타입. DB에는 멤버 이름이 아닌 값을 저장한다."""
    return Enum(enum_cls, name=name, values_callable=lambda e: [m.value for m in e])
