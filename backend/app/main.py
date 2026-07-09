from fastapi import FastAPI

app = FastAPI(
    title="CareFlow API",
    description="검사 결과 기반 건강상담 운영 플랫폼",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
