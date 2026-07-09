"""QR 진입 검증 — docs/04 §4.10 테스트 전략 7번 (NFR-7의 증명):
위변조 토큰 거부, 이름/전화 불일치 403, 시도 횟수 제한, 스코프 세션 최소 권한."""

import pytest

from app.security import decode_access_token
from app.services import consult as consult_service
from app.services.consult import MAX_ATTEMPTS, issue_qr_token
from tests.test_reservations import T, make_world


@pytest.fixture(autouse=True)
def _isolate_attempt_counter():
    consult_service.clear_attempts()
    yield
    consult_service.clear_attempts()


def test_forged_token_rejected(client, db):
    w = make_world(db)
    token = issue_qr_token(w.results[0].id)
    forged = token[:-3] + ("AAA" if not token.endswith("AAA") else "BBB")

    assert client.get("/consult", params={"t": forged}).status_code == 400
    assert client.get("/consult", params={"t": "garbage"}).status_code == 400


def test_valid_token_returns_masked_info(client, db):
    w = make_world(db)
    token = issue_qr_token(w.results[0].id)

    res = client.get("/consult", params={"t": token})
    assert res.status_code == 200
    body = res.json()
    assert body["subject_name_masked"] == "고**"  # "고객1" → 첫 글자만
    assert body["service_type"] == "comprehensive_metabolic"


def test_verify_success_issues_scoped_session(client, db):
    w = make_world(db)
    token = issue_qr_token(w.results[0].id)

    res = client.post(
        "/consult/verify",
        json={"token": token, "name": "고객1", "phone": "010-0000-0001"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["test_result_id"] == w.results[0].id

    payload = decode_access_token(body["access_token"])
    assert payload["scope"] == f"consult:{w.results[0].id}"
    assert payload["sub"] == str(w.customers[0].id)


def test_verify_phone_format_tolerant(client, db):
    """하이픈 유무·공백은 검증 통과에 영향 없어야 함 (숫자만 비교)."""
    w = make_world(db)
    token = issue_qr_token(w.results[0].id)
    res = client.post(
        "/consult/verify",
        json={"token": token, "name": "고객1", "phone": "01000000001"},
    )
    assert res.status_code == 200


def test_mismatch_403_then_lockout_429(client, db):
    """불일치 5회 → 잠금. 잠긴 뒤에는 올바른 정보로도 거부 (무차별 대입 차단)."""
    w = make_world(db)
    token = issue_qr_token(w.results[0].id)

    for _ in range(MAX_ATTEMPTS):
        res = client.post(
            "/consult/verify",
            json={"token": token, "name": "고객1", "phone": "010-9999-9999"},
        )
        assert res.status_code == 403

    res = client.post(
        "/consult/verify",
        json={"token": token, "name": "고객1", "phone": "010-0000-0001"},
    )
    assert res.status_code == 429


def _scoped_headers(client, db, w, result_idx=0):
    token = issue_qr_token(w.results[result_idx].id)
    res = client.post(
        "/consult/verify",
        json={"token": token, "name": "고객1", "phone": "010-0000-0001"},
    )
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_scoped_session_blocked_from_other_apis(client, db):
    """스코프 세션은 명시 허용 엔드포인트 외 전부 차단 (최소 권한)."""
    w = make_world(db)
    headers = _scoped_headers(client, db, w)

    assert client.get("/auth/me", headers=headers).status_code == 403
    assert client.get("/me/reservations", headers=headers).status_code == 403
    # 스코프 밖 결과지 조회도 차단 (고객1 소유의 다른 결과지여도)
    other = client.get(f"/test-results/{w.results[2].id}", headers=headers)
    assert other.status_code == 403


def test_scoped_session_allows_only_its_flow(client, db):
    """허용 범위: 해당 결과지 조회 + 그 결과지 예약 생성. 다른 결과지 예약은 403."""
    w = make_world(db)
    headers = _scoped_headers(client, db, w)

    assert (
        client.get(f"/test-results/{w.results[0].id}", headers=headers).status_code
        == 200
    )
    assert (
        client.get("/slots", params={"date": T.date().isoformat()}, headers=headers)
        .status_code == 200
    )

    wrong = client.post(
        "/reservations",
        headers=headers,
        json={
            "start_at": T.isoformat(),
            "subject_id": w.subjects[0].id,
            "test_result_id": w.results[2].id,  # 스코프 밖 결과지
        },
    )
    assert wrong.status_code == 403

    ok = client.post(
        "/reservations",
        headers=headers,
        json={
            "start_at": T.isoformat(),
            "subject_id": w.subjects[0].id,
            "test_result_id": w.results[0].id,
        },
    )
    assert ok.status_code == 201
