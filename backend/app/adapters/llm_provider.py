from abc import ABC, abstractmethod
from functools import lru_cache
from itertools import count
from typing import Any

from app.config import get_settings

# 상담 기록 구조화 스키마 — tool use로 강제해 파싱 실패·환각 필드를 차단 (§4.5)
EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary": {"type": "string", "description": "상담 내용 2~3문장 요약"},
        "interested_products": {
            "type": "array", "items": {"type": "string"},
            "description": "고객이 관심을 보인 제품·영양소",
        },
        "recommendations": {
            "type": "array", "items": {"type": "string"},
            "description": "상담사가 안내한 권장 사항",
        },
        "follow_up": {"type": "string", "description": "후속 조치·재상담 계획, 없으면 빈 문자열"},
        "purchase_linked": {"type": "boolean", "description": "구매 의사·구매 발생 언급 여부"},
    },
    "required": ["summary", "interested_products", "recommendations", "follow_up", "purchase_linked"],
}


class LLMProvider(ABC):
    """LLM 계약 (NFR-3): 실패해도 핵심 플로우가 동작해야 하므로 항상 보조 수단."""

    @abstractmethod
    def extract_record(self, raw_memo: str) -> dict[str, Any]:
        """자유 메모 → 구조화 초안 (동기)."""

    @abstractmethod
    def submit_briefing_batch(self, requests: list[tuple[str, dict]]) -> str:
        """(custom_id, 비식별 페이로드) 목록 제출 → batch_id (비동기 배치)."""

    @abstractmethod
    def fetch_batch_results(self, batch_id: str) -> dict[str, str] | None:
        """완료 시 {custom_id: 브리핑 텍스트}, 아직 처리 중이면 None."""


class MockLLMProvider(LLMProvider):
    """결정론 목 (NFR-10): API 키 없이 전 플로우 재현. 같은 입력 → 항상 같은 출력.

    규칙 기반이라 데모·테스트가 재현 가능하고, 실 프로바이더와 동일한
    배치 수명주기(submit → poll)를 흉내 내 스케줄러 경로까지 검증한다.
    """

    PRODUCT_KEYWORDS = (
        "오메가3", "유산균", "프로바이오틱스", "비타민D", "비타민B", "비타민",
        "마그네슘", "아연", "엽산", "셀레늄", "밀크씨슬", "홍삼",
    )

    def __init__(self) -> None:
        self._batches: dict[str, dict[str, str]] = {}
        self._seq = count(1)

    def extract_record(self, raw_memo: str) -> dict[str, Any]:
        lines = [ln.strip() for ln in raw_memo.splitlines() if ln.strip()]
        products: list[str] = []
        for kw in self.PRODUCT_KEYWORDS:
            if kw in raw_memo and kw not in products:
                products.append(kw)
        recommendations = [
            ln for ln in lines if any(w in ln for w in ("권장", "추천", "제안", "안내"))
        ][:5]
        follow_up = next(
            (ln for ln in lines if any(w in ln for w in ("재상담", "후속", "다음 상담", "팔로업"))),
            "",
        )
        summary = " ".join(lines)[:150]
        return {
            "summary": summary,
            "interested_products": products,
            "recommendations": recommendations,
            "follow_up": follow_up,
            "purchase_linked": "구매" in raw_memo,
        }

    def submit_briefing_batch(self, requests: list[tuple[str, dict]]) -> str:
        batch_id = f"mock-batch-{next(self._seq)}"
        self._batches[batch_id] = {
            custom_id: self._briefing_text(payload) for custom_id, payload in requests
        }
        return batch_id

    def fetch_batch_results(self, batch_id: str) -> dict[str, str] | None:
        # 목은 즉시 완료 — 첫 폴링에서 결과 반환
        return self._batches.get(batch_id, {})

    @staticmethod
    def _briefing_text(payload: dict) -> str:
        parts = [f"[사전 브리핑] {payload.get('service_type', '')} 결과 상담"]
        for ind in payload.get("indicators", []):
            parts.append(
                f"- {ind.get('name')}: {ind.get('value')}{ind.get('unit', '')}"
                f" (참고범위 {ind.get('range')}) — {ind.get('comment', '')}"
            )
        pre_q = payload.get("pre_question")
        if pre_q:
            parts.append(f"고객 사전 문의: \"{pre_q}\" — 이 주제를 우선 다루세요.")
        return "\n".join(parts)


class AnthropicProvider(LLMProvider):
    """실 프로바이더. 추출은 동기 + tool use 스키마 강제,
    브리핑은 Message Batches(비용 50% 절감, §4.5)."""

    MODEL = "claude-sonnet-5"

    def __init__(self, api_key: str) -> None:
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)

    def extract_record(self, raw_memo: str) -> dict[str, Any]:
        message = self._client.messages.create(
            model=self.MODEL,
            max_tokens=1024,
            tools=[{
                "name": "save_record",
                "description": "상담 메모에서 구조화된 기록을 추출해 저장한다",
                "input_schema": EXTRACTION_SCHEMA,
            }],
            tool_choice={"type": "tool", "name": "save_record"},
            messages=[{
                "role": "user",
                "content": f"다음 건강상담 메모에서 기록을 추출하세요:\n\n{raw_memo}",
            }],
        )
        for block in message.content:
            if block.type == "tool_use":
                return block.input
        raise RuntimeError("구조화 추출 실패: tool_use 블록 없음")

    def submit_briefing_batch(self, requests: list[tuple[str, dict]]) -> str:
        batch = self._client.messages.batches.create(
            requests=[
                {
                    "custom_id": custom_id,
                    "params": {
                        "model": self.MODEL,
                        "max_tokens": 1024,
                        "messages": [{
                            "role": "user",
                            "content": (
                                "전화 건강상담사가 상담 전 참고할 브리핑을 작성하세요. "
                                "핵심 지표와 우선 논의 주제를 간결히.\n\n"
                                f"{payload}"
                            ),
                        }],
                    },
                }
                for custom_id, payload in requests
            ]
        )
        return batch.id

    def fetch_batch_results(self, batch_id: str) -> dict[str, str] | None:
        batch = self._client.messages.batches.retrieve(batch_id)
        if batch.processing_status != "ended":
            return None
        results: dict[str, str] = {}
        for entry in self._client.messages.batches.results(batch_id):
            if entry.result.type == "succeeded":
                results[entry.custom_id] = entry.result.message.content[0].text
        return results


@lru_cache
def get_llm_provider() -> LLMProvider:
    """키가 있으면 실 API, 없으면 결정론 목 — 동일 코드 경로 (NFR-10)."""
    api_key = get_settings().anthropic_api_key
    return AnthropicProvider(api_key) if api_key else MockLLMProvider()
