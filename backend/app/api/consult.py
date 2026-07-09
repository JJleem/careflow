from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.schemas.consult import (
    ConsultInfoResponse,
    ConsultVerifyRequest,
    ScopedSessionResponse,
)
from app.services import consult as consult_service

router = APIRouter(prefix="/consult", tags=["QR 진입"])

DB = Annotated[Session, Depends(get_db)]


def _mask(name: str) -> str:
    return name[0] + "*" * (len(name) - 1) if name else ""


@router.get("")
def resolve_token(db: DB, t: Annotated[str, Query()]) -> ConsultInfoResponse:
    """QR 스캔 직후: 토큰 서명 검증 → 검증 화면에 띄울 최소 정보."""
    try:
        tr = consult_service.get_test_result_for_token(db, t)
    except consult_service.InvalidQrToken:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="유효하지 않은 QR 코드입니다"
        )
    return ConsultInfoResponse(
        service_type=tr.service_type,
        reported_at=tr.reported_at,
        subject_name_masked=_mask(tr.subject.name),
    )


@router.post("/verify")
def verify(db: DB, body: ConsultVerifyRequest) -> ScopedSessionResponse:
    try:
        token, tr, _owner = consult_service.verify_and_issue_session(
            db, body.token, body.name, body.phone
        )
    except consult_service.InvalidQrToken:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="유효하지 않은 QR 코드입니다"
        )
    except consult_service.TooManyAttempts:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail="시도 횟수를 초과했습니다. 잠시 후 다시 시도해 주세요",
        )
    except consult_service.IdentityMismatch:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="이름 또는 전화번호가 일치하지 않습니다"
        )
    return ScopedSessionResponse(
        access_token=token,
        test_result_id=tr.id,
        subject_id=tr.subject_id,
        expires_in_minutes=get_settings().scoped_session_expire_minutes,
    )
