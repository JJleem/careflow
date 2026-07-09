import re
import time

from itsdangerous import BadSignature, URLSafeTimedSerializer
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import TestResult, User
from app.security import create_access_token

MAX_ATTEMPTS = 5
LOCK_SECONDS = 600

# 결과지별 검증 실패 카운터. MVP는 인프로세스로 충분 —
# 다중 워커 실운영에서는 Redis 카운터로 교체 (어댑터 지점)
_failed_attempts: dict[int, tuple[int, float]] = {}


class InvalidQrToken(Exception):
    pass


class IdentityMismatch(Exception):
    pass


class TooManyAttempts(Exception):
    pass


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().secret_key, salt="qr-consult")


def issue_qr_token(test_result_id: int) -> str:
    """결과지 인쇄 시점에 QR로 인코딩되는 서명 토큰. raw ID 노출(IDOR) 차단이 목적."""
    return _serializer().dumps({"tr": test_result_id})


def parse_qr_token(token: str) -> int:
    try:
        payload = _serializer().loads(
            token, max_age=get_settings().qr_token_max_age_seconds
        )
    except BadSignature as exc:  # SignatureExpired 포함
        raise InvalidQrToken from exc
    return int(payload["tr"])


def _normalize_phone(phone: str) -> str:
    return re.sub(r"\D", "", phone)


def _check_lock(test_result_id: int) -> None:
    count, last_at = _failed_attempts.get(test_result_id, (0, 0.0))
    if count >= MAX_ATTEMPTS and time.monotonic() - last_at < LOCK_SECONDS:
        raise TooManyAttempts


def _register_failure(test_result_id: int) -> None:
    count, _ = _failed_attempts.get(test_result_id, (0, 0.0))
    _failed_attempts[test_result_id] = (count + 1, time.monotonic())


def clear_attempts() -> None:
    """테스트 격리용."""
    _failed_attempts.clear()


def get_test_result_for_token(db: Session, token: str) -> TestResult:
    tr = db.get(TestResult, parse_qr_token(token))
    if tr is None:
        raise InvalidQrToken
    return tr


def verify_and_issue_session(
    db: Session, token: str, name: str, phone: str
) -> tuple[str, TestResult, User]:
    """2요소 검증: 결과지 실물 소지(서명 토큰) + 소유 계정의 이름/전화 일치 (§4.3-7).

    통과 시 스코프 제한 세션(짧은 TTL) 발급. 검증 강도에 비례한 최소 권한 (NFR-7).
    """
    tr = get_test_result_for_token(db, token)
    _check_lock(tr.id)

    owner = tr.subject.owner
    if (
        owner.name != name.strip()
        or _normalize_phone(owner.phone) != _normalize_phone(phone)
    ):
        _register_failure(tr.id)
        raise IdentityMismatch

    _failed_attempts.pop(tr.id, None)
    settings = get_settings()
    access_token = create_access_token(
        owner.id,
        owner.role,
        expires_minutes=settings.scoped_session_expire_minutes,
        scope=f"consult:{tr.id}",
    )
    return access_token, tr, owner
