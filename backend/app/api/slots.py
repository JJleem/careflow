from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_auth_context, require_roles
from app.db import get_db
from app.models import User, UserRole
from app.schemas.slot import (
    AvailableTimesResponse,
    DateAlternative,
    SlotCreate,
    SlotResponse,
    TimeAvailability,
)
from app.services import slots as slot_service

router = APIRouter(tags=["슬롯"])

CounselorUser = Annotated[User, Depends(require_roles(UserRole.counselor))]
DB = Annotated[Session, Depends(get_db)]


def _my_profile_id(db: Session, user: User) -> int:
    profile = slot_service.get_counselor_profile(db, user.id)
    if profile is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="상담사 프로필이 없습니다"
        )
    return profile.id


@router.get("/me/slots")
def my_slots(
    user: CounselorUser,
    db: DB,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> list[SlotResponse]:
    rows = slot_service.list_my_slots(db, _my_profile_id(db, user), date_from, date_to)
    return [
        SlotResponse(
            id=slot.id,
            start_at=slot.start_at,
            end_at=slot.end_at,
            has_active_reservation=has_active,
        )
        for slot, has_active in rows
    ]


@router.post("/me/slots", status_code=status.HTTP_201_CREATED)
def create_slot(user: CounselorUser, db: DB, body: SlotCreate) -> SlotResponse:
    counselor_id = _my_profile_id(db, user)
    try:
        slot = slot_service.create_slot(db, counselor_id, body.start_at)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="같은 시각에 이미 슬롯이 있습니다"
        )
    return SlotResponse(id=slot.id, start_at=slot.start_at, end_at=slot.end_at)


@router.delete("/me/slots/{slot_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_slot(user: CounselorUser, db: DB, slot_id: int) -> None:
    try:
        slot_service.delete_slot(db, _my_profile_id(db, user), slot_id)
    except slot_service.SlotNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="슬롯이 없습니다")
    except slot_service.SlotHasActiveReservation:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="활성 예약이 있는 슬롯은 삭제할 수 없습니다. 예약 취소로 처리하세요",
        )


@router.get("/slots")
def available_times(
    ctx: Annotated[AuthContext, Depends(get_auth_context)],
    db: DB,
    target_date: Annotated[date, Query(alias="date")],
) -> AvailableTimesResponse:
    # QR 스코프 세션도 예약 화면을 그려야 하므로 허용 (가용 시간은 민감정보 아님)
    if ctx.user.role != UserRole.customer:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="권한이 없습니다")
    times = slot_service.list_available_times(db, target_date)
    alternatives = (
        slot_service.find_alternative_dates(db, target_date) if not times else []
    )
    return AvailableTimesResponse(
        date=target_date,
        times=[
            TimeAvailability(start_at=s, end_at=e, available_count=c)
            for s, e, c in times
        ],
        alternatives=[
            DateAlternative(date=d, available_count=c) for d, c in alternatives
        ],
    )
