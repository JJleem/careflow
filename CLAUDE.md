# CareFlow — 검사 결과 기반 건강상담 운영 플랫폼

대사체 분석 결과지를 받은 고객의 1:1 전화 상담 운영(예약 → 리마인드 → 상담 → 기록 → 지표)을 자동화하는 풀스택 프로젝트. 가상 헬스케어 기업 "바이오컴" 시나리오 기반.

## 세션 시작 시 필독

새 세션에서는 아래 순서로 맥락을 잡을 것:

1. 이 파일의 **진행 상태** 섹션 (지난 세션이 어디서 멈췄는지)
2. `docs/04-system-design.md` — 아키텍처·ERD·API·운영 정책 (구현의 기준 문서)
3. 필요시 `docs/01~03` — 문제 정의, 요구사항 목록(FR/NFR ID), MVP 범위 근거
4. 프론트 작업 시 `docs/05-design-system.md`(컬러 토큰·타이포·상태 뱃지 — 임의 색상 금지) + `docs/06-frontend-design.md`(라우팅·상태·API 계층·세션 전략)

설계 관련 결정은 전부 docs/에 근거와 함께 기록되어 있다. **문서와 다르게 구현하게 되면 반드시 문서를 먼저 고치고 커밋할 것** (문서 = single source of truth).

## 진행 상태

- [x] 기획·설계 문서 4종 (docs/01~04) — 설계 확정, 설계 리뷰(엣지 케이스 정책) 완료
- [x] 디자인 시스템 명세 (docs/05) — 컬러 토큰·타이포·상태 뱃지 매핑
- [x] 프론트엔드 설계 (docs/06) — TanStack Query·openapi-typescript 코드젠·토큰 저장 전략·라우팅 맵
- [x] 백엔드 골격: FastAPI 구조, SQLAlchemy 모델 11종, Alembic(제약 3종 실증), docker-compose(db 5433 + backend), 멱등 시드
- [x] 예약 코어 완료 (테스트 13종): 인증(8434dbf) → 슬롯 API(0f8e1f0) → 예약 생성+동시성 6종(e385d9a) → 상태 전이+가드 7종(9f08003)
- [x] QR 진입: 서명 토큰 발급/검증(위변조·잠금 테스트), 스코프 세션(허용 3개 API 외 일괄 차단), 결과지 상세/QR 딥링크 API (e8d1660)
- [x] 알림: 인앱 채널 어댑터(NFR-4, 실패 시 재시도 계약), APScheduler 폴링 60초 + 대기 만료 1시간, 알림함 API (1b0f84a)
- [x] LLM: 기록 구조화(동기, 스키마 강제) + 브리핑(배치 submit/poll 잡), 결정론 MockProvider 폴백(NFR-10), 비식별화(NFR-9) (78d93f5)
- [x] 구매 웹훅 + 어트리뷰션: HMAC 서명, order_id 멱등, completed_at 기준 30일, 최근 1건 연결 (523fc0a)
- [x] 피검자 API + 관리자 지표(GET /admin/metrics — 완료율/노쇼율/전환율/제품 순위) (441daa2) — **백엔드 전체 완성, 테스트 39종**
- [ ] 프론트: 고객(결과지/QR/예약), 상담사(워크스페이스/기록/슬롯), 관리자(대시보드)
- [ ] E2E 스모크 (Playwright): golden path — QR/로그인 진입 → 예약 → 완료 처리 → 기록 → 대시보드 반영
- [ ] README (실행 방법, 데모 시나리오, **스크린샷**, golden path 서사, 산출물 6종 매핑 표)

## 구현 품질 기준선

- API 키·외부 계정 **없이** `docker compose up` + 시드만으로 전 기능 재현 (NFR-10)
- 설계 결정마다 테스트로 증명: 동시성(2중 제약), 상태 전이 가드, 접근 제어, 웹훅 멱등성
- 커밋은 기능 단위로 작게, 문서-구현 어긋나면 문서 먼저 수정
- README는 평가자 동선 기준: TL;DR → 실행 1커맨드 → golden path → 산출물 매핑 → 설계 근거 링크

> 세션을 마칠 때 이 체크리스트와 아래 "직전 세션 메모"를 갱신하고 커밋할 것.

**직전 세션 메모 (2026-07-09)**: 백엔드 골격 완료 + 예약 코어 대부분 완료. ① 원커맨드 구동(마이그레이션→멱등 시드→서버), db 호스트 포트 5433(로컬 PG 충돌 회피) ② ERD 정합화 3건 문서 먼저 수정 ③ JWT 인증(가입 customer 고정, 로그인 실패 메시지 단일화) ④ 슬롯 API(30분 격자, 삭제 가드, 시간대 통합 조회) ⑤ 예약 생성(재상담 우선→부하 최소 배정, insert-first + savepoint 차순위 재시도, 알림·리마인더·브리핑 원자 생성, 만석 409에 대안 추천) ⑥ **테스트 13종 통과** (careflow_test DB, 실 PG — barrier 동시성 2종 포함) ⑦ 상태 전이 완료: 시점 가드, 취소 사이드이펙트 4종(리마인더는 notification.reservation_id로 해당 예약 것만 삭제 — ERD에 FK 추가, 문서 먼저), completed_at/no_show_at 컬럼 추가(마이그레이션 2번째). ⑧ QR 진입 완료: itsdangerous 서명 토큰(1년), 이름/전화 2요소 검증(5회 실패→10분 잠금, 인메모리 — 실운영 Redis 교체 지점), 스코프 세션은 JWT scope 클레임("consult:<tr_id>")으로 구현 — get_current_user가 스코프 토큰을 일괄 거부하고 명시 허용 3곳(결과지 조회·슬롯 조회·해당 결과지 예약)만 get_auth_context 사용. ⑨ 알림 스케줄러 완료: 채널 어댑터 뒤 발송, lifespan에서 기동(테스트는 scheduler_enabled=False로 끔 — conftest autouse), 라이브 틱 검증까지. ⑩ **백엔드 전체 완성** (테스트 39종): LLM(MockProvider 결정론 폴백 — 키 없이 전 플로우, AnthropicProvider는 tool use 스키마 강제 + Message Batches), 구매 웹훅(HMAC·멱등·30일 어트리뷰션), 피검자/관리자 지표 API. 시드 계정 demo1234. 배포는 안 함(완료 후 옵션 — 사용자와 합의). **다음 작업: 프론트엔드** (React+TS+Vite, docs/05 디자인 시스템 준수 — 임의 색상 금지. 고객: 결과지/QR/예약, 상담사: 워크스페이스, 관리자: 대시보드). 사용자는 프론트 개발자 — 백엔드 개념은 프론트 비유로. 면접노트는 interview-notes.local.md 누적(커밋 금지).

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
