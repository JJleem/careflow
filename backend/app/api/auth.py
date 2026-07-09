from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import get_db
from app.models import User, UserRole
from app.schemas.auth import LoginRequest, SignupRequest, TokenResponse, UserResponse
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["인증"])


def _token_response(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        user=UserResponse.model_validate(user),
    )


@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(
    body: SignupRequest, db: Annotated[Session, Depends(get_db)]
) -> TokenResponse:
    if db.scalar(select(User.id).where(User.email == body.email)):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="이미 가입된 이메일입니다")
    # 자가 가입은 고객만 — 상담사/관리자는 시드(운영 프로비저닝) 경로로만 생성
    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        role=UserRole.customer,
        name=body.name,
        phone=body.phone,
    )
    db.add(user)
    db.commit()
    return _token_response(user)


@router.post("/login")
def login(body: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == body.email))
    # 미가입/비밀번호 오류를 구분해 알려주지 않는다 (계정 존재 여부 노출 방지)
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="이메일 또는 비밀번호가 올바르지 않습니다"
        )
    return _token_response(user)


@router.get("/me")
def me(user: Annotated[User, Depends(get_current_user)]) -> UserResponse:
    return UserResponse.model_validate(user)
