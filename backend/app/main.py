from fastapi import FastAPI

from app.api import auth

app = FastAPI(
    title="CareFlow API",
    description="검사 결과 기반 건강상담 운영 플랫폼",
    version="0.1.0",
)

app.include_router(auth.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
