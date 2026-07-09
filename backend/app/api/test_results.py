from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_auth_context, require_roles
from app.db import get_db
from app.models import (
    ACTIVE_STATUSES,
    AvailabilitySlot,
    CounselorProfile,
    Reservation,
    TestResult,
    User,
    UserRole,
)
from app.schemas.consult import ConsultTokenResponse, TestResultResponse
from app.services import consult as consult_service

router = APIRouter(prefix="/test-results", tags=["결과지"])

DB = Annotated[Session, Depends(get_db)]


def _is_assigned_counselor(db: Session, user: User, test_result_id: int) -> bool:
    """배정 상담사 = 이 결과지의 활성 예약이 걸린 슬롯의 상담사 (§4.6 권한 규칙)."""
    return bool(
        db.scalar(
            select(
                exists()
                .where(Reservation.test_result_id == test_result_id)
                .where(Reservation.status.in_(ACTIVE_STATUSES))
                .where(Reservation.slot_id == AvailabilitySlot.id)
                .where(AvailabilitySlot.counselor_id == CounselorProfile.id)
                .where(CounselorProfile.user_id == user.id)
            )
        )
    )


@router.get("/{test_result_id}")
def get_test_result(
    ctx: Annotated[AuthContext, Depends(get_auth_context)],
    db: DB,
    test_result_id: int,
) -> TestResultResponse:
    """접근 허용: 소유 고객 / 배정 상담사 / 이 결과지의 QR 스코프 세션."""
    tr = db.get(TestResult, test_result_id)
    if tr is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="결과지가 없습니다")

    if ctx.scoped_test_result_id is not None:
        allowed = ctx.scoped_test_result_id == test_result_id
    elif ctx.user.role == UserRole.customer:
        allowed = tr.subject.owner_user_id == ctx.user.id
    elif ctx.user.role == UserRole.counselor:
        allowed = _is_assigned_counselor(db, ctx.user, test_result_id)
    else:
        allowed = False

    if not allowed:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="이 결과지를 볼 권한이 없습니다"
        )
    return TestResultResponse.model_validate(tr)


@router.get("/{test_result_id}/consult-token")
def get_consult_token(
    user: Annotated[User, Depends(require_roles(UserRole.customer))],
    db: DB,
    test_result_id: int,
) -> ConsultTokenResponse:
    """결과지 상세 화면의 QR 이미지·딥링크용. 실물 인쇄분과 동일한 토큰 (§4.7 진입점 이원화)."""
    tr = db.get(TestResult, test_result_id)
    if tr is None or tr.subject.owner_user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="결과지가 없습니다")
    token = consult_service.issue_qr_token(tr.id)
    return ConsultTokenResponse(token=token, url=f"/consult?t={token}")
