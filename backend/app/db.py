from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

engine = create_engine(get_settings().database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """요청 단위 DB 세션. FastAPI Depends로 주입되며 요청 종료 시 반드시 닫힌다."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
