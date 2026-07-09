from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User, UserRole
from app.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class AuthContext:
    """인증된 요청의 주체. scoped_test_result_id가 있으면 QR 스코프 세션 —
    해당 결과지 조회와 그 결과지 예약만 허용된다 (NFR-7)."""

    user: User
    scoped_test_result_id: int | None = None


def get_auth_context(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
    db: Annotated[Session, Depends(get_db)],
) -> AuthContext:
    if credentials is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="인증 토큰이 필요합니다"
        )
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="유효하지 않거나 만료된 토큰입니다"
        )
    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="존재하지 않는 사용자입니다"
        )

    scoped_test_result_id = None
    scope = payload.get("scope")
    if scope is not None:
        prefix, _, raw_id = scope.partition(":")
        if prefix != "consult" or not raw_id.isdigit():
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED, detail="유효하지 않은 토큰입니다"
            )
        scoped_test_result_id = int(raw_id)
    return AuthContext(user=user, scoped_test_result_id=scoped_test_result_id)


def get_current_user(
    ctx: Annotated[AuthContext, Depends(get_auth_context)],
) -> User:
    """정식 로그인 전용. 스코프 세션은 여기서 전부 차단되므로
    명시적으로 허용한 엔드포인트(get_auth_context 사용) 외에는 접근 불가."""
    if ctx.scoped_test_result_id is not None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="QR 세션으로는 접근할 수 없습니다. 로그인해 주세요",
        )
    return ctx.user


def require_roles(*roles: UserRole):
    """역할 가드 의존성 팩토리. 인가 규칙 일원화 지점 (NFR-2)."""

    def checker(
        user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="권한이 없습니다")
        return user

    return checker
