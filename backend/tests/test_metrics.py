"""지표 집계 정확성(§4.10-4) + 피검자 접근 제어(§4.10-5)."""

from datetime import date, datetime, timedelta, timezone

from app.models import DraftSource, ReservationStatus
from app.security import create_access_token
from app.services.metrics import compute_metrics
from app.services.records import save_record
from tests.test_reservations import make_world
from tests.test_transitions import make_past_reservation


def _finish(db, w, status, *, with_record=False, purchase_linked=False, products=()):
    r = make_past_reservation(db, w)
    r.status = status
    if status == ReservationStatus.completed:
        r.completed_at = datetime.now(timezone.utc)
    db.commit()
    if with_record:
        save_record(
            db, r.id, w.counselors[0],
            raw_memo="m", summary=None, interested_products=list(products),
            recommendations=[], follow_up=None, purchase_linked=purchase_linked,
            draft_source=DraftSource.manual,
        )
    return r


def test_metrics_rates_and_product_ranking(db):
    """완료2(전환1)·노쇼1·취소1 → 완료율 0.5, 노쇼율 1/3, 전환율 0.5, 제품 순위."""
    w = make_world(db)
    _finish(db, w, ReservationStatus.completed, with_record=True,
            purchase_linked=True, products=("오메가3", "비타민D"))
    _finish(db, w, ReservationStatus.completed, with_record=True,
            products=("오메가3",))
    _finish(db, w, ReservationStatus.no_show)
    _finish(db, w, ReservationStatus.cancelled)

    today = date.today()
    m = compute_metrics(db, today - timedelta(days=7), today + timedelta(days=7))

    assert m["total_reservations"] == 4
    assert m["completed"] == 2
    assert m["no_show"] == 1
    assert m["cancelled"] == 1
    assert m["completion_rate"] == 0.5
    assert m["no_show_rate"] == round(1 / 3, 4)
    assert m["conversion_rate"] == 0.5
    assert m["top_interested_products"][0] == {"product": "오메가3", "count": 2}


def test_metrics_empty_period_returns_none_rates(db):
    """0건 기간에 0으로 나누지 않는다 — 비율은 None."""
    make_world(db)
    past = date(2020, 1, 1)
    m = compute_metrics(db, past, past)
    assert m["total_reservations"] == 0
    assert m["no_show_rate"] is None
    assert m["conversion_rate"] is None


def test_admin_metrics_endpoint_role_guard(client, db):
    w = make_world(db)
    params = {"from": "2026-07-01", "to": "2026-07-31"}
    customer = {"Authorization": f"Bearer {create_access_token(w.customers[0].id, 'customer')}"}
    assert client.get("/admin/metrics", params=params, headers=customer).status_code == 403


def test_subject_access_control(client, db):
    """타인 피검자 결과 조회 → 404 (존재 비노출, §4.10-5)."""
    w = make_world(db)
    other = {"Authorization": f"Bearer {create_access_token(w.customers[1].id, 'customer')}"}
    owner = {"Authorization": f"Bearer {create_access_token(w.customers[0].id, 'customer')}"}

    mine = client.get(f"/subjects/{w.subjects[0].id}/test-results", headers=owner)
    assert mine.status_code == 200
    assert len(mine.json()) == 2  # 고객1 피검자의 결과지 2건

    stolen = client.get(f"/subjects/{w.subjects[0].id}/test-results", headers=other)
    assert stolen.status_code == 404
