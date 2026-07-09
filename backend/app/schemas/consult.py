from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models import ServiceType


class ConsultInfoResponse(BaseModel):
    """검증 화면용 최소 정보. 이름은 마스킹 — 검증 전이므로 개인정보 비노출."""

    service_type: ServiceType
    reported_at: date
    subject_name_masked: str


class ConsultVerifyRequest(BaseModel):
    token: str
    name: str = Field(min_length=1, max_length=50)
    phone: str = Field(min_length=9, max_length=20)


class ScopedSessionResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    test_result_id: int
    subject_id: int
    expires_in_minutes: int


class ConsultTokenResponse(BaseModel):
    token: str
    url: str


class TestResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subject_id: int
    service_type: ServiceType
    reported_at: date
    indicators: list[dict[str, Any]]
