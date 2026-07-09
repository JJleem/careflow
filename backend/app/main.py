from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import (
    admin,
    auth,
    consult,
    notifications,
    records,
    reservations,
    slots,
    subjects,
    test_results,
    webhooks,
)
from app.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = None
    if get_settings().scheduler_enabled:
        from app.scheduler import create_scheduler

        scheduler = create_scheduler()
        scheduler.start()
    yield
    if scheduler is not None:
        scheduler.shutdown(wait=False)


app = FastAPI(
    title="CareFlow API",
    description="검사 결과 기반 건강상담 운영 플랫폼",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(slots.router)
app.include_router(reservations.router)
app.include_router(consult.router)
app.include_router(test_results.router)
app.include_router(notifications.router)
app.include_router(records.router)
app.include_router(webhooks.router)
app.include_router(subjects.router)
app.include_router(admin.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
