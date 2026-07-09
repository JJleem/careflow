from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.adapters.llm_provider import get_llm_provider
from app.api.deps import require_roles
from app.db import get_db
from app.models import Reservation, User, UserRole
from app.schemas.record import (
    BriefingResponse,
    ExtractRequest,
    RecordDraft,
    RecordResponse,
    RecordSaveRequest,
)
from app.services import briefings as briefing_service
from app.services import records as record_service

router = APIRouter(tags=["상담 기록"])

CounselorUser = Annotated[User, Depends(require_roles(UserRole.counselor))]
DB = Annotated[Session, Depends(get_db)]


@router.post("/records/extract")
def extract_draft(user: CounselorUser, body: ExtractRequest) -> RecordDraft:
    """메모 → 구조화 초안. 상담사가 검수·수정 후 저장하는 휴먼 인 더 루프 (§4.5).

    LLM 장애 시에도 수기 작성 경로(/reservations/{id}/record)는 그대로 동작 (NFR-3).
    """
    raw = get_llm_provider().extract_record(body.raw_memo)
    return RecordDraft.model_validate(raw)  # 스키마 검증으로 환각 필드 차단


@router.post("/reservations/{reservation_id}/record", status_code=status.HTTP_201_CREATED)
def save_record(
    user: CounselorUser, db: DB, reservation_id: int, body: RecordSaveRequest
) -> RecordResponse:
    try:
        record = record_service.save_record(
            db,
            reservation_id,
            user,
            raw_memo=body.raw_memo,
            summary=body.summary,
            interested_products=body.interested_products,
            recommendations=body.recommendations,
            follow_up=body.follow_up,
            purchase_linked=body.purchase_linked,
            draft_source=body.draft_source,
        )
    except record_service.ReservationNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="예약이 없습니다")
    except record_service.NotAssignedCounselor:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="배정된 상담사만 기록할 수 있습니다"
        )
    except record_service.ReservationNotCompleted:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="완료 처리된 상담만 기록할 수 있습니다"
        )
    except record_service.RecordAlreadyExists:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="이미 기록이 저장된 상담입니다"
        )
    return RecordResponse.model_validate(record)


@router.get("/reservations/{reservation_id}/record")
def get_record(
    user: CounselorUser, db: DB, reservation_id: int
) -> RecordResponse:
    record = record_service.get_record(db, reservation_id)
    if record is None or record.reservation.slot.counselor.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="기록이 없습니다")
    return RecordResponse.model_validate(record)


@router.get("/reservations/{reservation_id}/briefing")
def get_briefing(
    user: CounselorUser, db: DB, reservation_id: int
) -> BriefingResponse:
    reservation = db.get(Reservation, reservation_id)
    if reservation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="예약이 없습니다")
    if reservation.slot.counselor.user_id != user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="배정된 상담사만 볼 수 있습니다"
        )
    briefing = briefing_service.get_briefing(db, reservation_id)
    if briefing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="브리핑이 없습니다")
    return BriefingResponse.model_validate(briefing)
