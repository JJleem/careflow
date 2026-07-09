from datetime import date, datetime, timezone

from pydantic import BaseModel, ConfigDict, field_validator


class SlotCreate(BaseModel):
    start_at: datetime

    @field_validator("start_at")
    @classmethod
    def validate_start_at(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("타임존 정보가 필요합니다 (예: 2026-07-15T10:00:00+09:00)")
        # 30분 격자 강제: (counselor_id, start_at) unique가 겹침 차단으로 충분해지는 전제
        if v.minute not in (0, 30) or v.second or v.microsecond:
            raise ValueError("슬롯은 정시 또는 30분 단위로만 개설할 수 있습니다")
        if v <= datetime.now(timezone.utc):
            raise ValueError("과거 시각에는 슬롯을 개설할 수 없습니다")
        return v


class SlotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    start_at: datetime
    end_at: datetime
    has_active_reservation: bool = False


class TimeAvailability(BaseModel):
    start_at: datetime
    end_at: datetime
    available_count: int


class DateAlternative(BaseModel):
    date: date
    available_count: int


class AvailableTimesResponse(BaseModel):
    date: date
    times: list[TimeAvailability]
    # 해당 날짜 만석일 때만 채워짐: 예약 가능한 가장 가까운 날짜들 (P3 이탈 방지)
    alternatives: list[DateAlternative]
