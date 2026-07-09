FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# 의존성 레이어 분리: 코드만 바뀌면 설치를 다시 하지 않도록 (빌드 캐시)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .
ENV PATH="/app/.venv/bin:$PATH"

# 마이그레이션 → 시드 → 서버. 원커맨드 구동의 핵심 (NFR-6)
CMD ["sh", "-c", "alembic upgrade head && python seed.py && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
