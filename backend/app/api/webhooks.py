from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy.orm import Session

from app.db import get_db
from app.services import purchases as purchase_service

router = APIRouter(prefix="/webhooks", tags=["웹훅"])

DB = Annotated[Session, Depends(get_db)]


class PurchasePayload(BaseModel):
    order_id: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=9, max_length=20)
    product_name: str = Field(min_length=1, max_length=200)
    occurred_at: datetime

    @field_validator("occurred_at")
    @classmethod
    def require_timezone(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("타임존 정보가 필요합니다")
        return v


class PurchaseAck(BaseModel):
    order_id: str
    created: bool
    matched: bool


@router.post("/purchase")
async def receive_purchase(
    request: Request,
    db: DB,
    x_signature: Annotated[str | None, Header()] = None,
) -> PurchaseAck:
    """자사몰 주문 웹훅 (§4.5). 서명은 원문 바이트 기준 HMAC — 파싱 전에 검증한다."""
    body = await request.body()
    if not purchase_service.verify_signature(body, x_signature):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="서명이 유효하지 않습니다"
        )
    try:
        payload = PurchasePayload.model_validate_json(body)
    except ValidationError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()
        )

    event, created = purchase_service.ingest_purchase(
        db,
        order_id=payload.order_id,
        customer_phone=payload.phone,
        product_name=payload.product_name,
        occurred_at=payload.occurred_at,
    )
    return PurchaseAck(
        order_id=event.order_id,
        created=created,
        matched=event.matched_record_id is not None,
    )
