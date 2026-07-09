"""테스트 DB 셋업. 실제 PostgreSQL(careflow_test)을 쓴다 —
검증 대상이 partial unique index·GiST EXCLUDE 같은 PG 고유 제약이라
SQLite 대체는 테스트 자체를 무의미하게 만들기 때문."""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.models import Base

TEST_DB_NAME = "careflow_test"


@pytest.fixture(scope="session", autouse=True)
def _disable_scheduler():
    """TestClient의 lifespan이 스케줄러를 띄우지 않도록 — 잡은 SessionLocal(개발 DB)을
    쓰므로 테스트 격리가 깨진다. 스케줄러 잡 로직은 서비스 함수 단위로 직접 테스트."""
    get_settings().scheduler_enabled = False


@pytest.fixture(scope="session")
def engine():
    base_url = get_settings().database_url
    admin_engine = create_engine(base_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        exists = conn.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :n"),
            {"n": TEST_DB_NAME},
        )
        if not exists:
            conn.execute(text(f"CREATE DATABASE {TEST_DB_NAME}"))
    admin_engine.dispose()

    test_url = base_url.rsplit("/", 1)[0] + f"/{TEST_DB_NAME}"
    eng = create_engine(test_url)
    with eng.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist"))
    # 모델이 바뀌어도 테스트 DB가 항상 최신 스키마가 되도록 재생성
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session_factory(engine):
    """테스트마다 전체 테이블 초기화 후 세션 팩토리 제공.
    동시성 테스트가 스레드별 독립 세션을 필요로 해서 세션이 아닌 팩토리를 준다."""
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE users RESTART IDENTITY CASCADE"))
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def db(session_factory):
    s = session_factory()
    yield s
    s.close()


@pytest.fixture
def client(session_factory):
    """테스트 DB로 연결된 HTTP 클라이언트 — 접근 제어처럼
    라우터·의존성 레이어까지 검증해야 하는 테스트용."""
    from fastapi.testclient import TestClient

    from app.db import get_db
    from app.main import app

    def override():
        s = session_factory()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
