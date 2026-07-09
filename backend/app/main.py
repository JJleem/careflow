from fastapi import FastAPI

from app.api import auth, consult, reservations, slots, test_results

app = FastAPI(
    title="CareFlow API",
    description="검사 결과 기반 건강상담 운영 플랫폼",
    version="0.1.0",
)

app.include_router(auth.router)
app.include_router(slots.router)
app.include_router(reservations.router)
app.include_router(consult.router)
app.include_router(test_results.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
