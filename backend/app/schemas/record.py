from pydantic import BaseModel, ConfigDict, Field

from app.models import BriefingStatus, DraftSource


class ExtractRequest(BaseModel):
    raw_memo: str = Field(min_length=1, max_length=10000)


class RecordDraft(BaseModel):
    """LLM 추출 결과의 스키마 검증 — 환각 필드·형식 오류를 여기서 한 번 더 차단."""

    summary: str
    interested_products: list[str]
    recommendations: list[str]
    follow_up: str
    purchase_linked: bool


class RecordSaveRequest(BaseModel):
    raw_memo: str = Field(min_length=1, max_length=10000)
    summary: str | None = None
    interested_products: list[str] = []
    recommendations: list[str] = []
    follow_up: str | None = None
    purchase_linked: bool = False
    draft_source: DraftSource = DraftSource.manual


class RecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reservation_id: int
    raw_memo: str
    summary: str | None
    interested_products: list[str]
    recommendations: list[str]
    follow_up: str | None
    purchase_linked: bool
    draft_source: DraftSource


class BriefingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: BriefingStatus
    content: str | None
