from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import get_settings

ALGORITHM = "HS256"


def hash_password(raw: str) -> str:
    return bcrypt.hashpw(raw.encode(), bcrypt.gensalt()).decode()


def verify_password(raw: str, hashed: str) -> bool:
    return bcrypt.checkpw(raw.encode(), hashed.encode())


def create_access_token(
    user_id: int,
    role: str,
    *,
    expires_minutes: int | None = None,
    scope: str | None = None,
) -> str:
    """scope가 있으면 스코프 제한 세션 — 짧은 TTL과 함께 쓴다 (NFR-7)."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now
        + timedelta(minutes=expires_minutes or settings.access_token_expire_minutes),
    }
    if scope is not None:
        payload["scope"] = scope
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """만료·서명 불일치 시 jwt.PyJWTError 계열 예외를 던진다."""
    return jwt.decode(token, get_settings().secret_key, algorithms=[ALGORITHM])
