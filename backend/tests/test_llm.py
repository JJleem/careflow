"""LLM 검증 — docs/04 §4.10-6: 추출 스키마 검증(프로바이더는 목),
브리핑 배치 수명주기, 기록 저장 가드. Mock의 결정론(NFR-10)도 확인."""

from sqlalchemy import select

from app.adapters.llm_provider import MockLLMProvider
from app.models import (
    Briefing,
    BriefingStatus,
    DraftSource,
    ReservationStatus,
)
from app.schemas.record import RecordDraft
from app.security import create_access_token
from app.services.briefings import (
    poll_processing_briefings,
    submit_pending_briefings,
)
from app.services.records import (
    NotAssignedCounselor,
    RecordAlreadyExists,
    ReservationNotCompleted,
    save_record,
)
from tests.test_reservations import make_world
from tests.test_transitions import make_past_reservation

MEMO = """공복혈당이 경계 수준이라 걱정하심.
정제 탄수화물 줄이고 식후 걷기를 권장함.
오메가3와 비타민D 보충에 관심 보이심. 구매 의사 있음.
4주 뒤 재상담 예정."""


def test_mock_extraction_is_deterministic_and_schema_valid():
    provider = MockLLMProvider()
    first = provider.extract_record(MEMO)
    second = provider.extract_record(MEMO)

    assert first == second  # 결정론 (NFR-10)
    draft = RecordDraft.model_validate(first)  # 스키마 검증 통과
    assert "오메가3" in draft.interested_products
    assert "비타민D" in draft.interested_products
    assert draft.purchase_linked is True
    assert "재상담" in draft.follow_up
    assert any("권장" in r for r in draft.recommendations)


def test_briefing_batch_lifecycle(db):
    """pending → (제출) processing → (폴링) done + 비식별 내용 생성."""
    from app.services.reservations import create_reservation
    from tests.test_reservations import T

    w = make_world(db)
    r = create_reservation(
        db, w.customers[0].id, w.subjects[0].id, w.results[0].id, T,
        pre_question="혈당이 걱정돼요",
    )
    provider = MockLLMProvider()

    assert submit_pending_briefings(db, provider) == 1
    briefing = db.scalar(select(Briefing).where(Briefing.reservation_id == r.id))
    assert briefing.status == BriefingStatus.processing

    assert poll_processing_briefings(db, provider) == 1
    assert briefing.status == BriefingStatus.done
    assert "사전 브리핑" in briefing.content
    assert "혈당이 걱정돼요" in briefing.content
    # 비식별화 (NFR-9): 고객 이름이 페이로드에 없어야 함
    assert "고객1" not in briefing.content


def test_stale_pending_briefing_cancelled_not_submitted(db):
    """예약이 이미 종결(no_show 등)인 pending 브리핑은 제출 대신 취소 (§4.7)."""
    w = make_world(db)
    r = make_past_reservation(db, w)
    r.status = ReservationStatus.no_show
    db.add(Briefing(reservation_id=r.id))
    db.commit()

    assert submit_pending_briefings(db, MockLLMProvider()) == 0
    briefing = db.scalar(select(Briefing).where(Briefing.reservation_id == r.id))
    assert briefing.status == BriefingStatus.cancelled


def test_save_record_guards(db):
    """배정 상담사만·완료 건만·예약당 1건."""
    w = make_world(db, counselors=2)
    r = make_past_reservation(db, w)
    kwargs = dict(
        raw_memo=MEMO, summary="요약", interested_products=["오메가3"],
        recommendations=[], follow_up=None, purchase_linked=False,
        draft_source=DraftSource.llm,
    )

    try:
        save_record(db, r.id, w.counselors[0], **kwargs)
        raise AssertionError("완료 전 기록은 차단되어야 한다")
    except ReservationNotCompleted:
        pass

    r.status = ReservationStatus.completed
    db.commit()

    try:
        save_record(db, r.id, w.counselors[1], **kwargs)  # 미배정 상담사
        raise AssertionError("차단되어야 한다")
    except NotAssignedCounselor:
        pass

    record = save_record(db, r.id, w.counselors[0], **kwargs)
    assert record.draft_source == DraftSource.llm

    try:
        save_record(db, r.id, w.counselors[0], **kwargs)
        raise AssertionError("중복 기록은 차단되어야 한다")
    except RecordAlreadyExists:
        pass


def test_extract_endpoint_returns_validated_draft(client, db):
    w = make_world(db)
    headers = {
        "Authorization": f"Bearer {create_access_token(w.counselors[0].id, 'counselor')}"
    }
    res = client.post("/records/extract", headers=headers, json={"raw_memo": MEMO})
    assert res.status_code == 200
    body = res.json()
    assert set(body) == {
        "summary", "interested_products", "recommendations", "follow_up", "purchase_linked",
    }
