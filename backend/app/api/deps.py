from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User, UserRole
from app.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
    db: Annotated[Session, Depends(get_db)],
) -> User:
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
    return user


def require_roles(*roles: UserRole):
    """역할 가드 의존성 팩토리. 인가 규칙 일원화 지점 (NFR-2)."""

    def checker(
        user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="권한이 없습니다")
        return user

    return checker
