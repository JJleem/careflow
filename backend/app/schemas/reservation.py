from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import ReservationStatus


class ReservationCreate(BaseModel):
    start_at: datetime
    subject_id: int
    test_result_id: int
    pre_question: str | None = Field(default=None, max_length=2000)

    @field_validator("start_at")
    @classmethod
    def require_timezone(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("타임존 정보가 필요합니다 (예: 2026-07-15T10:00:00+09:00)")
        return v


class ReservationTransitionRequest(BaseModel):
    status: ReservationStatus

    @field_validator("status")
    @classmethod
    def not_confirmed(cls, v: ReservationStatus) -> ReservationStatus:
        if v == ReservationStatus.confirmed:
            raise ValueError("confirmed로는 전이할 수 없습니다 (생성 시에만 부여)")
        return v


class ReservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: ReservationStatus
    start_at: datetime
    end_at: datetime
    subject_id: int
    test_result_id: int
    counselor_name: str
    pre_question: str | None
