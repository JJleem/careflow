from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """환경변수 기반 설정. 전부 기본값이 있어 키·외부 계정 없이 구동된다 (NFR-10)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # 호스트 포트 5433 = docker-compose가 노출하는 db 포트 (로컬 PG와 충돌 회피)
    database_url: str = "postgresql+psycopg://careflow:careflow@localhost:5433/careflow"

    # JWT / QR 서명 토큰. 데모용 기본값(HS256 권장 32바이트 이상) — 실운영에서는 반드시 환경변수로 주입
    secret_key: str = "careflow-dev-only-secret-key-change-in-production"
    access_token_expire_minutes: int = 60 * 24
    qr_token_max_age_seconds: int = 60 * 60 * 24 * 365  # 결과지 인쇄물 수명
    scoped_session_expire_minutes: int = 30  # QR 스코프 세션 짧은 TTL (NFR-7)

    # 비어 있으면 결정론 MockProvider로 폴백 (NFR-10)
    anthropic_api_key: str = ""

    webhook_secret: str = "careflow-webhook-secret"

    timezone: str = "Asia/Seoul"  # 표시·해석 타임존, 저장은 UTC (NFR-8)

    scheduler_enabled: bool = True  # 테스트에서는 끔 (잡이 테스트 DB 밖을 건드리지 않도록)


@lru_cache
def get_settings() -> Settings:
    return Settings()
