from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.llm_provider import LLMProvider
from app.models import Briefing, BriefingStatus, Reservation, ReservationStatus


def _build_payload(r: Reservation) -> dict:
    """LLM 전송 페이로드 — 이름·연락처 등 식별자 제거, 지표·해설·사전 문의만 (NFR-9)."""
    tr = r.test_result
    return {
        "service_type": tr.service_type.value,
        "indicators": tr.indicators,
        "pre_question": r.pre_question or "",
    }


def submit_pending_briefings(db: Session, provider: LLMProvider) -> int:
    """pending 브리핑을 배치로 제출. 활성(confirmed) 예약 건만 포함하고
    이미 무의미해진 건(완료·노쇼된 예약)은 취소 처리한다 (§4.7)."""
    rows = db.execute(
        select(Briefing, Reservation)
        .join(Reservation, Briefing.reservation_id == Reservation.id)
        .where(Briefing.status == BriefingStatus.pending)
    ).all()
    if not rows:
        return 0

    requests: list[tuple[str, dict]] = []
    submitted: list[Briefing] = []
    for briefing, reservation in rows:
        if reservation.status != ReservationStatus.confirmed:
            briefing.status = BriefingStatus.cancelled
            continue
        requests.append((str(briefing.id), _build_payload(reservation)))
        submitted.append(briefing)

    if requests:
        batch_id = provider.submit_briefing_batch(requests)
        for briefing in submitted:
            briefing.status = BriefingStatus.processing
            briefing.batch_id = batch_id
    db.commit()
    return len(submitted)


def poll_processing_briefings(db: Session, provider: LLMProvider) -> int:
    """processing 배치 폴링 → 완료 시 content 저장. 결과 누락 건은 failed —
    브리핑은 참고 자료이므로 실패해도 상담 플로우에 영향 없음 (NFR-3)."""
    processing = list(
        db.scalars(
            select(Briefing).where(Briefing.status == BriefingStatus.processing)
        )
    )
    done = 0
    by_batch: dict[str, list[Briefing]] = {}
    for b in processing:
        by_batch.setdefault(b.batch_id or "", []).append(b)

    for batch_id, briefings in by_batch.items():
        results = provider.fetch_batch_results(batch_id)
        if results is None:  # 아직 처리 중
            continue
        for b in briefings:
            content = results.get(str(b.id))
            if content:
                b.content = content
                b.status = BriefingStatus.done
                done += 1
            else:
                b.status = BriefingStatus.failed
    db.commit()
    return done


def get_briefing(db: Session, reservation_id: int) -> Briefing | None:
    return db.scalar(
        select(Briefing).where(Briefing.reservation_id == reservation_id)
    )
