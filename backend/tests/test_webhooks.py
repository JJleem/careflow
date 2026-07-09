"""구매 웹훅 검증 — docs/04 §4.10-8: 서명 검증, 멱등성(재전송 무시),
30일 윈도우 매칭/미매칭, 최근 상담 1건 연결."""

import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.config import get_settings
from app.models import DraftSource, PurchaseEvent, ReservationStatus
from app.services.records import save_record
from tests.test_reservations import make_world
from tests.test_transitions import make_past_reservation


def _signed_post(client, payload: dict, *, bad_signature=False):
    body = json.dumps(payload).encode()
    sig = hmac.new(
        get_settings().webhook_secret.encode(), body, hashlib.sha256
    ).hexdigest()
    if bad_signature:
        sig = "0" * 64
    return client.post(
        "/webhooks/purchase",
        content=body,
        headers={"X-Signature": sig, "Content-Type": "application/json"},
    )


def _completed_consultation_with_record(db, w, completed_hours_ago=1):
    """완료 상담 + 기록 생성 (어트리뷰션 대상)."""
    r = make_past_reservation(db, w, hours_ago=completed_hours_ago)
    r.status = ReservationStatus.completed
    r.completed_at = datetime.now(timezone.utc) - timedelta(hours=completed_hours_ago)
    db.commit()
    return save_record(
        db, r.id, w.counselors[0],
        raw_memo="메모", summary=None, interested_products=[],
        recommendations=[], follow_up=None, purchase_linked=False,
        draft_source=DraftSource.manual,
    )


def _payload(order_id="ORD-1", phone="010-0000-0001", days_after_consult=1):
    return {
        "order_id": order_id,
        "phone": phone,
        "product_name": "오메가3",
        "occurred_at": (
            datetime.now(timezone.utc) + timedelta(days=days_after_consult)
        ).isoformat(),
    }


def test_invalid_signature_rejected(client, db):
    res = _signed_post(client, _payload(), bad_signature=True)
    assert res.status_code == 401


def test_idempotent_resend_ignored(client, db):
    """같은 order_id 재수신 → 이벤트 1건 유지, created=false (§4.7 멱등성)."""
    make_world(db)
    first = _signed_post(client, _payload())
    second = _signed_post(client, _payload())

    assert first.json()["created"] is True
    assert second.json()["created"] is False
    assert db.scalar(select(func.count()).select_from(PurchaseEvent)) == 1


def test_attribution_within_window(client, db):
    """완료 후 30일 이내 + 전화 일치 → purchase_linked, 하이픈 없어도 매칭."""
    w = make_world(db)
    record = _completed_consultation_with_record(db, w)

    res = _signed_post(client, _payload(phone="01000000001"))
    assert res.json()["matched"] is True
    db.refresh(record)
    assert record.purchase_linked is True


def test_attribution_outside_window_or_wrong_phone(client, db):
    """윈도우 밖(31일 후) 또는 전화 불일치 → 매칭 없음, 이벤트는 보존."""
    w = make_world(db)
    record = _completed_consultation_with_record(db, w)

    late = _payload(order_id="ORD-LATE", days_after_consult=31)
    wrong = _payload(order_id="ORD-WRONG", phone="010-9999-9999")
    assert _signed_post(client, late).json()["matched"] is False
    assert _signed_post(client, wrong).json()["matched"] is False

    db.refresh(record)
    assert record.purchase_linked is False
    assert db.scalar(select(func.count()).select_from(PurchaseEvent)) == 2


def test_attribution_picks_most_recent_consultation(client, db):
    """후보 여러 건이면 가장 최근 완료 상담 1건에만 연결."""
    w = make_world(db)
    older = _completed_consultation_with_record(db, w, completed_hours_ago=48)
    newer = _completed_consultation_with_record(db, w, completed_hours_ago=1)

    res = _signed_post(client, _payload())
    assert res.json()["matched"] is True
    db.refresh(older)
    db.refresh(newer)
    assert newer.purchase_linked is True
    assert older.purchase_linked is False
