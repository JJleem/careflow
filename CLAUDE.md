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
- [x] 프론트 디자인 토큰 초안 (`frontend/src/styles/tokens.css`) — docs/05 토큰 → Tailwind `@theme` + shadcn/ui 변수 매핑
- [x] 백엔드 골격: FastAPI 구조, SQLAlchemy 모델 11종, Alembic(제약 3종 실증), docker-compose(db 5433 + backend), 멱등 시드
- [x] 예약 코어 완료 (테스트 13종): 인증(8434dbf) → 슬롯 API(0f8e1f0) → 예약 생성+동시성 6종(e385d9a) → 상태 전이+가드 7종(9f08003)
- [x] QR 진입: 서명 토큰 발급/검증(위변조·잠금 테스트), 스코프 세션(허용 3개 API 외 일괄 차단), 결과지 상세/QR 딥링크 API (e8d1660)
- [x] 알림: 인앱 채널 어댑터(NFR-4, 실패 시 재시도 계약), APScheduler 폴링 60초 + 대기 만료 1시간, 알림함 API (1b0f84a)
- [x] LLM: 기록 구조화(동기, 스키마 강제) + 브리핑(배치 submit/poll 잡), 결정론 MockProvider 폴백(NFR-10), 비식별화(NFR-9) (78d93f5)
- [x] 구매 웹훅 + 어트리뷰션: HMAC 서명, order_id 멱등, completed_at 기준 30일, 최근 1건 연결 (523fc0a)
- [x] 피검자 API + 관리자 지표(GET /admin/metrics — 완료율/노쇼율/전환율/제품 순위) (441daa2) — **백엔드 전체 완성, 테스트 39종**
- [x] 프론트 골격: Vite React19+TS+Tailwind v4, openapi-typescript+openapi-fetch(schema.d.ts 커밋), zustand auth/QR 스코프 세션, 라우팅 맵+역할 가드, shadcn 셋업(05 토큰 강제), 로그인/가입 동작 검증 (fb7bf50→1833bdb)
- [x] 고객 화면 완료: 결과지 목록/상세(지표 판정·상담 QR), QR 진입(본인확인→스코프 세션), 예약(만석 대안 UI), 내 예약(취소 다이얼로그), 알림함(30초 폴링) — Playwright 스크린샷+클릭스루 검증 (6a74bc0, dfbf489)
- [ ] 프론트 화면: 상담사(워크스페이스/기록/슬롯), 관리자(대시보드)
- [ ] E2E 스모크 (Playwright): golden path — QR/로그인 진입 → 예약 → 완료 처리 → 기록 → 대시보드 반영
- [ ] README (실행 방법, 데모 시나리오, **스크린샷**, golden path 서사, 산출물 6종 매핑 표)

## 구현 품질 기준선

- API 키·외부 계정 **없이** `docker compose up` + 시드만으로 전 기능 재현 (NFR-10)
- 설계 결정마다 테스트로 증명: 동시성(2중 제약), 상태 전이 가드, 접근 제어, 웹훅 멱등성
- 커밋은 기능 단위로 작게, 문서-구현 어긋나면 문서 먼저 수정
- README는 평가자 동선 기준: TL;DR → 실행 1커맨드 → golden path → 산출물 매핑 → 설계 근거 링크

> 세션을 마칠 때 이 체크리스트와 아래 "직전 세션 메모"를 갱신하고 커밋할 것.

**직전 세션 메모 (2026-07-10)**: 프론트 골격 + 인증 화면 완료. ① Vite React 19+TS 5.9 골격 생성 — React 19는 라이브러리 전부 지원이라 문서 먼저 갱신(c323c11), TS는 openapi-typescript peer(`^5.x`) 충돌로 5.9 고정. Tailwind v4는 `@tailwindcss/vite` 플러그인, dev 프록시 `/api`→`:8000` rewrite. ② API 계층: `openapi-fetch` 추가 채택(문서 244c38e — 수동 래퍼는 드리프트 차단이 절반만 실현) + `schema.d.ts`는 서버 없이 `uv run python`으로 `app.openapi()` 덤프 후 생성·커밋, 재생성은 `npm run codegen`(백엔드 기동 필요). ③ auth: zustand persist(`cf.auth`/localStorage) + QR 스코프 세션(`cf.scoped`/sessionStorage) 분리, client 미들웨어가 스코프 토큰 우선 주입, 401 전역 처리(단 `/auth/*`의 401은 화면 인라인). ④ 라우팅 맵 §6.3 전체 배선 + RequireRole(미인증→login, 역할 불일치→역할 홈, `/reserve`는 스코프 세션 허용). 화면 10종은 아직 placeholder. ⑤ shadcn 셋업: button/input/label/card, CLI가 기본 팔레트 미주입 확인, 시맨틱 변수 전부 05 토큰 통과, rounded-sm/md/lg/xl→2/4/10/20px 매핑(향후 컴포넌트 자동 준수), 카드 rounded-card+shadow-card·버튼 hover=primary-dark 보정. **주의: shadcn CLI는 루트 tsconfig.json에 paths 없으면 리터럴 `@/` 폴더를 만든다(등록해둠)**. ⑥ 로그인/가입 실동작: 성공 시 역할 홈 리다이렉트, 401/409 인라인 에러. 검증 = compose 백엔드 기동 후 프록시 경유 로그인 200/오답 401, 빌드+oxlint 통과. ⑦ **톤 전환(같은 날)**: 사용자 피드백 "관공서같이 정적, 토스처럼 고급지게" → docs/05 §5.3 톤 보정 커밋(8c15558) 후 구현(a549b36). radius 8/12/16/24, 무테두리 카드+부드러운 그림자, 채움형 인풋(포커스 시 흰 배경+민트 링), 버튼 h-12 semibold press scale·비활성 회색→채우면 민트, surface #F2F4F4, 제목 700/-0.02em, 해요체 카피(05 §5.5-5). **중요 함정: tailwind-merge가 커스텀 타입 토큰(text-body 등)을 색상으로 오인해 진짜 색상 클래스를 제거함 → `lib/utils.ts`의 extendTailwindMerge에 font-size 그룹 등록으로 해결(새 타입 토큰 추가 시 여기도 추가할 것)**. Playwright(devDep, chromium 설치됨)로 스크린샷·클릭스루 검증하는 패턴 확립 — 앞으로 화면 작업마다 스크린샷 자가검증. ⑧ **고객 화면 완료(같은 날, 6a74bc0·dfbf489)**: 공용 기반(쿼리 훅 4파일·ApiError(409 분기 응답 보존)·StatusBadge(05 §5.1 매핑)·Empty/ErrorState·CustomerLayout(미읽음 도트, 스코프 세션 시 내비 숨김))+화면 5종+QR 진입. 예약 컨텍스트는 쿼리 파라미터(결과지 CTA) 또는 스코프 세션 필수 — 없으면 결과지 안내. shadcn badge/dialog/skeleton/textarea 추가(채움형·rounded-modal 보정). 시간은 lib/datetime.ts의 Intl Asia/Seoul(NFR-8), 서비스명/알림종류 한글은 lib/labels.ts, 지표 정상/주의는 range 문자열("70~99"/"x 미만"/"x 이상") 해석(불가 시 칩 생략). 검증: Playwright로 예약 생성→확정→내 예약→취소 다이얼로그, 비로그인 QR 검증(오답 403·위변조 400 화면 포함)→스코프 예약, 알림함(스케줄러 발송분 표시) 전부 스크린샷 확인. 데모 DB에 테스트 예약 1건 생성됨(7/10 14:00 — 필요 시 컨테이너 재생성으로 시드 리셋). ⑨ 다음 시작점: 상담사 화면(/work/today 당일 일정+브리핑+완료/노쇼 → /work/records/:id 기록+AI 구조화 → /work/slots 주간 슬롯) → 관리자 대시보드 → E2E → README. 상담사 레이아웃은 밀도 높은 업무 톤(05 §5.4). 사용자는 프론트 개발자 — 백엔드 개념은 프론트 비유로. 면접노트는 `interview-notes.local.md` 누적(커밋 금지).

## 스택 및 구조

- Backend: FastAPI (Python 3.12) + SQLAlchemy 2.0 + PostgreSQL + Alembic + APScheduler
- Frontend: React 19 + TypeScript + Vite
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
