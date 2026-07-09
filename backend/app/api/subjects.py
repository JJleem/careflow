from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db import get_db
from app.models import Subject, TestResult, User, UserRole
from app.schemas.consult import TestResultResponse
from app.schemas.subject import SubjectCreate, SubjectResponse

router = APIRouter(prefix="/subjects", tags=["피검자"])

CustomerUser = Annotated[User, Depends(require_roles(UserRole.customer))]
DB = Annotated[Session, Depends(get_db)]


@router.get("")
def my_subjects(user: CustomerUser, db: DB) -> list[SubjectResponse]:
    rows = db.scalars(
        select(Subject).where(Subject.owner_user_id == user.id).order_by(Subject.id)
    )
    return [SubjectResponse.model_validate(s) for s in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_subject(user: CustomerUser, db: DB, body: SubjectCreate) -> SubjectResponse:
    subject = Subject(
        owner_user_id=user.id,
        name=body.name,
        birth_date=body.birth_date,
        relation=body.relation,
    )
    db.add(subject)
    db.commit()
    return SubjectResponse.model_validate(subject)


@router.get("/{subject_id}/test-results")
def subject_test_results(
    user: CustomerUser, db: DB, subject_id: int
) -> list[TestResultResponse]:
    subject = db.get(Subject, subject_id)
    # 타인 피검자는 404 — 존재 여부 자체를 노출하지 않음 (NFR-2)
    if subject is None or subject.owner_user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="피검자가 없습니다")
    rows = db.scalars(
        select(TestResult)
        .where(TestResult.subject_id == subject_id)
        .order_by(TestResult.reported_at.desc())
    )
    return [TestResultResponse.model_validate(tr) for tr in rows]
