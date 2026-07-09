from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db import get_db
from app.models import Reservation, User, UserRole
from app.schemas.reservation import (
    ReservationCreate,
    ReservationResponse,
    ReservationTransitionRequest,
)
from app.services import reservations as reservation_service
from app.services import slots as slot_service

router = APIRouter(tags=["예약"])

CustomerUser = Annotated[User, Depends(require_roles(UserRole.customer))]
DB = Annotated[Session, Depends(get_db)]


def _to_response(r: Reservation) -> ReservationResponse:
    return ReservationResponse(
        id=r.id,
        status=r.status,
        start_at=r.start_at,
        end_at=r.end_at,
        subject_id=r.subject_id,
        test_result_id=r.test_result_id,
        counselor_name=r.slot.counselor.user.name,
        pre_question=r.pre_question,
    )


@router.post("/reservations", status_code=status.HTTP_201_CREATED)
def create_reservation(
    user: CustomerUser, db: DB, body: ReservationCreate
) -> ReservationResponse:
    try:
        reservation = reservation_service.create_reservation(
            db,
            customer_id=user.id,
            subject_id=body.subject_id,
            test_result_id=body.test_result_id,
            start_at=body.start_at,
            pre_question=body.pre_question,
        )
    except reservation_service.SubjectNotOwned:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="본인 피검자가 아닙니다")
    except reservation_service.TestResultNotFound:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="해당 피검자의 결과지가 아닙니다"
        )
    except reservation_service.InvalidStartTime:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="과거 시각에는 예약할 수 없습니다"
        )
    except reservation_service.DuplicateReservation as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=exc.reason)
    except reservation_service.NoAvailableSlot:
        db.rollback()
        day = body.start_at.date()
        same_day = slot_service.list_available_times(db, day)
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail={
                "message": "해당 시각은 만석입니다",
                "alternative_times": [
                    {"start_at": s.isoformat(), "available_count": c}
                    for s, _, c in same_day
                ],
                "alternative_dates": [
                    {"date": d.isoformat(), "available_count": c}
                    for d, c in (
                        slot_service.find_alternative_dates(db, day)
                        if not same_day
                        else []
                    )
                ],
            },
        )
    return _to_response(reservation)


@router.patch("/reservations/{reservation_id}")
def transition_reservation(
    user: Annotated[User, Depends(get_current_user)],
    db: DB,
    reservation_id: int,
    body: ReservationTransitionRequest,
) -> ReservationResponse:
    try:
        reservation = reservation_service.transition_reservation(
            db, reservation_id, body.status, actor=user
        )
    except reservation_service.ReservationNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="예약이 없습니다")
    except reservation_service.PermissionDenied:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="이 예약을 변경할 권한이 없습니다"
        )
    except reservation_service.InvalidTransition as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=exc.reason)
    return _to_response(reservation)


@router.get("/me/reservations")
def my_reservations(
    user: Annotated[User, Depends(get_current_user)], db: DB
) -> list[ReservationResponse]:
    if user.role == UserRole.customer:
        rows = reservation_service.list_my_reservations_as_customer(db, user.id)
    elif user.role == UserRole.counselor:
        profile = slot_service.get_counselor_profile(db, user.id)
        if profile is None:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, detail="상담사 프로필이 없습니다"
            )
        rows = reservation_service.list_my_reservations_as_counselor(db, profile.id)
    else:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="권한이 없습니다")
    return [_to_response(r) for r in rows]
