# CareFlow — 검사 결과 기반 건강상담 운영 플랫폼

대사체 분석 결과지를 받은 고객의 1:1 전화 상담 운영(예약 → 리마인드 → 상담 → 기록 → 지표)을 자동화하는 풀스택 프로젝트. 가상 헬스케어 기업 "바이오컴" 시나리오 기반.

## 세션 시작 시 필독

새 세션에서는 아래 순서로 맥락을 잡을 것:

1. 이 파일의 **진행 상태** 섹션 (지난 세션이 어디서 멈췄는지)
2. `docs/04-system-design.md` — 아키텍처·ERD·API·운영 정책 (구현의 기준 문서)
3. 필요시 `docs/01~03` — 문제 정의, 요구사항 목록(FR/NFR ID), MVP 범위 근거
4. 프론트 작업 시 `docs/05-design-system.md` — 컬러 토큰·타이포·상태 뱃지 매핑 (임의 색상 추가 금지)

설계 관련 결정은 전부 docs/에 근거와 함께 기록되어 있다. **문서와 다르게 구현하게 되면 반드시 문서를 먼저 고치고 커밋할 것** (문서 = single source of truth).

## 진행 상태

- [x] 기획·설계 문서 4종 (docs/01~04) — 설계 확정, 설계 리뷰(엣지 케이스 정책) 완료
- [x] 디자인 시스템 명세 (docs/05) — 컬러 토큰·타이포·상태 뱃지 매핑
- [ ] 백엔드 골격: FastAPI 구조, SQLAlchemy 모델, Alembic, docker-compose, 시드
- [ ] 예약 코어: 슬롯/예약 API, 이중 예약 차단 2중 제약(슬롯 partial unique + 고객 시간겹침 GiST EXCLUDE) + 동시성 테스트
- [ ] QR 진입: 서명 토큰 발급/검증, 스코프 세션
- [ ] 알림: 인앱 채널 어댑터, APScheduler 리마인더(24h/1h)
- [ ] LLM: ① 기록 구조화(동기, structured output) ② 사전 브리핑(비동기 배치) — **키 없으면 결정론 MockProvider 폴백 필수 (NFR-10)**
- [ ] 구매 웹훅 + 어트리뷰션 (30일 윈도우)
- [ ] 프론트: 고객(결과지/QR/예약), 상담사(워크스페이스/기록/슬롯), 관리자(대시보드)
- [ ] E2E 스모크 (Playwright): golden path — QR/로그인 진입 → 예약 → 완료 처리 → 기록 → 대시보드 반영
- [ ] README (실행 방법, 데모 시나리오, **스크린샷**, golden path 서사, 산출물 6종 매핑 표)

## 구현 품질 기준선

- API 키·외부 계정 **없이** `docker compose up` + 시드만으로 전 기능 재현 (NFR-10)
- 설계 결정마다 테스트로 증명: 동시성(2중 제약), 상태 전이 가드, 접근 제어, 웹훅 멱등성
- 커밋은 기능 단위로 작게, 문서-구현 어긋나면 문서 먼저 수정
- README는 평가자 동선 기준: TL;DR → 실행 1커맨드 → golden path → 산출물 매핑 → 설계 근거 링크

> 세션을 마칠 때 이 체크리스트와 아래 "직전 세션 메모"를 갱신하고 커밋할 것.

**직전 세션 메모 (2026-07-08)**: 기획·설계 세션 종료. 산출물 = 설계 문서 5종(01~05) + 설계 리뷰 보강(04 §4.7 엣지 케이스 표: 진입점 이원화, 상담사 취소, 임박 리마인더, 노쇼 가드, 중복 예약, 웹훅 멱등성, 브리핑 취소, 스코프 세션, LLM 비식별화 NFR-9). 구현은 아직 시작 전 — **다음 작업: 백엔드 골격** (FastAPI 구조 + SQLAlchemy 모델 + Alembic + docker-compose + 시드, docs/04 §4.9 디렉터리 계획 따를 것).

## 스택 및 구조

- Backend: FastAPI (Python 3.12) + SQLAlchemy 2.0 + PostgreSQL + Alembic + APScheduler
- Frontend: React 18 + TypeScript + Vite
- LLM: Anthropic API (`LLMProvider` 어댑터 뒤에 추상화), 브리핑은 Message Batches
- 실행: docker-compose (db + backend + frontend), 시드 포함 원커맨드 목표 (NFR-6)
- 디렉터리 계획은 `docs/04-system-design.md` §4.9 참조

## 컨벤션

- 문서·커밋 메시지는 한국어, 커밋 prefix는 conventional commits (docs/feat/fix/chore/test)
- 시간: DB 저장 UTC(timestamptz), 표시·해석 Asia/Seoul 고정 (NFR-8)
- 이중 예약 차단은 반드시 DB 제약(partial unique index)으로 — 앱 로직 검사로 대체 금지 (NFR-1)
- LLM은 항상 보조 수단: 실패해도 핵심 플로우(예약/상담/기록)가 동작해야 함 (NFR-3)
- 외부 연동(알림 채널, LLM, 구매 이벤트)은 어댑터 인터페이스 뒤에만 둘 것

## 주의

- 이 레포는 **public**. 시나리오 원문 등 로컬 전용 파일은 `.git/info/exclude`에 등록되어 있으며(커밋 금지), 새 컴퓨터에서 clone 후 로컬 전용 파일을 가져오면 exclude에 다시 등록할 것.
- 민감한 로컬 메모는 `*.local.md` 패턴으로 만들면 .gitignore로 제외됨.
