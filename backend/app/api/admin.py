from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db import get_db
from app.models import User, UserRole
from app.schemas.metrics import MetricsResponse
from app.services.metrics import compute_metrics

router = APIRouter(prefix="/admin", tags=["관리자"])

AdminUser = Annotated[User, Depends(require_roles(UserRole.admin))]
DB = Annotated[Session, Depends(get_db)]


@router.get("/metrics")
def metrics(
    user: AdminUser,
    db: DB,
    date_from: Annotated[date, Query(alias="from")],
    date_to: Annotated[date, Query(alias="to")],
) -> MetricsResponse:
    if date_from > date_to:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="from은 to보다 이전이어야 합니다"
        )
    return MetricsResponse.model_validate(compute_metrics(db, date_from, date_to))
