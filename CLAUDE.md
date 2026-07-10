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
- [x] 상담사 워크스페이스 완료: 당일 일정(AI 브리핑 인라인·완료/노쇼 확인 다이얼로그), 기록 작성(AI 구조화→검수→저장, 실패 시 수기 경로), 슬롯 관리(30분 토글 그리드·예약 슬롯 잠금) — 골든패스 클릭스루 검증 (fbe5a80)
- [x] 관리자 대시보드 완료: 지표 카드 4종(총 예약/완료율/노쇼율/전환율)·상태 분해·관심 제품 순위·기간 토글. 백엔드 지표 응답을 MetricsResponse 스키마로 승격(dict→Pydantic, codegen 타입 유입) (a1dda81, 3d41c2c)
- [x] E2E 스모크 (Playwright) 12종: 인증·역할가드, 고객(결과지·지표판정·QR본인확인·예약생성→취소), 상담사(오늘일정·브리핑·슬롯토글), 관리자(지표). 취소 cleanup으로 멱등 — 재시드 없이 반복 통과. `npm run e2e` (6a1e096)
- [x] docker frontend 서비스 — 원커맨드 3서비스(db+backend+frontend, NFR-6). 멀티스테이지(node빌드→nginx), /api 프록시+SPA fallback, `docker compose up --build` → localhost:8080 (1e290ff)
- [ ] README (실행 방법, 데모 시나리오, **스크린샷**, golden path 서사, 산출물 6종 매핑 표)

## 구현 품질 기준선

- API 키·외부 계정 **없이** `docker compose up` + 시드만으로 전 기능 재현 (NFR-10)
- 설계 결정마다 테스트로 증명: 동시성(2중 제약), 상태 전이 가드, 접근 제어, 웹훅 멱등성
- 커밋은 기능 단위로 작게, 문서-구현 어긋나면 문서 먼저 수정
- README는 평가자 동선 기준: TL;DR → 실행 1커맨드 → golden path → 산출물 매핑 → 설계 근거 링크

> 세션을 마칠 때 이 체크리스트와 아래 "직전 세션 메모"를 갱신하고 커밋할 것.

**직전 세션 메모 (2026-07-10)**: 프론트 골격 + 인증 화면 완료. ① Vite React 19+TS 5.9 골격 생성 — React 19는 라이브러리 전부 지원이라 문서 먼저 갱신(c323c11), TS는 openapi-typescript peer(`^5.x`) 충돌로 5.9 고정. Tailwind v4는 `@tailwindcss/vite` 플러그인, dev 프록시 `/api`→`:8000` rewrite. ② API 계층: `openapi-fetch` 추가 채택(문서 244c38e — 수동 래퍼는 드리프트 차단이 절반만 실현) + `schema.d.ts`는 서버 없이 `uv run python`으로 `app.openapi()` 덤프 후 생성·커밋, 재생성은 `npm run codegen`(백엔드 기동 필요). ③ auth: zustand persist(`cf.auth`/localStorage) + QR 스코프 세션(`cf.scoped`/sessionStorage) 분리, client 미들웨어가 스코프 토큰 우선 주입, 401 전역 처리(단 `/auth/*`의 401은 화면 인라인). ④ 라우팅 맵 §6.3 전체 배선 + RequireRole(미인증→login, 역할 불일치→역할 홈, `/reserve`는 스코프 세션 허용). 화면 10종은 아직 placeholder. ⑤ shadcn 셋업: button/input/label/card, CLI가 기본 팔레트 미주입 확인, 시맨틱 변수 전부 05 토큰 통과, rounded-sm/md/lg/xl→2/4/10/20px 매핑(향후 컴포넌트 자동 준수), 카드 rounded-card+shadow-card·버튼 hover=primary-dark 보정. **주의: shadcn CLI는 루트 tsconfig.json에 paths 없으면 리터럴 `@/` 폴더를 만든다(등록해둠)**. ⑥ 로그인/가입 실동작: 성공 시 역할 홈 리다이렉트, 401/409 인라인 에러. 검증 = compose 백엔드 기동 후 프록시 경유 로그인 200/오답 401, 빌드+oxlint 통과. ⑦ **톤 전환(같은 날)**: 사용자 피드백 "관공서같이 정적, 토스처럼 고급지게" → docs/05 §5.3 톤 보정 커밋(8c15558) 후 구현(a549b36). radius 8/12/16/24, 무테두리 카드+부드러운 그림자, 채움형 인풋(포커스 시 흰 배경+민트 링), 버튼 h-12 semibold press scale·비활성 회색→채우면 민트, surface #F2F4F4, 제목 700/-0.02em, 해요체 카피(05 §5.5-5). **중요 함정: tailwind-merge가 커스텀 타입 토큰(text-body 등)을 색상으로 오인해 진짜 색상 클래스를 제거함 → `lib/utils.ts`의 extendTailwindMerge에 font-size 그룹 등록으로 해결(새 타입 토큰 추가 시 여기도 추가할 것)**. Playwright(devDep, chromium 설치됨)로 스크린샷·클릭스루 검증하는 패턴 확립 — 앞으로 화면 작업마다 스크린샷 자가검증. ⑧ **고객 화면 완료(같은 날, 6a74bc0·dfbf489)**: 공용 기반(쿼리 훅 4파일·ApiError(409 분기 응답 보존)·StatusBadge(05 §5.1 매핑)·Empty/ErrorState·CustomerLayout(미읽음 도트, 스코프 세션 시 내비 숨김))+화면 5종+QR 진입. 예약 컨텍스트는 쿼리 파라미터(결과지 CTA) 또는 스코프 세션 필수 — 없으면 결과지 안내. shadcn badge/dialog/skeleton/textarea 추가(채움형·rounded-modal 보정). 시간은 lib/datetime.ts의 Intl Asia/Seoul(NFR-8), 서비스명/알림종류 한글은 lib/labels.ts, 지표 정상/주의는 range 문자열("70~99"/"x 미만"/"x 이상") 해석(불가 시 칩 생략). 검증: Playwright로 예약 생성→확정→내 예약→취소 다이얼로그, 비로그인 QR 검증(오답 403·위변조 400 화면 포함)→스코프 예약, 알림함(스케줄러 발송분 표시) 전부 스크린샷 확인. 데모 DB에 테스트 예약 1건 생성됨(7/10 14:00 — 필요 시 컨테이너 재생성으로 시드 리셋). ⑨ **상담사 워크스페이스 완료(같은 날, fbe5a80)**: WorkLayout(넓은 컬럼·역할 뱃지)+화면 3종, 쿼리 훅 api/queries/counselor.ts(브리핑/기록 404는 에러 아닌 null), useTestResults 병렬 조회 추가. 검증 중 데모 예약을 SQL로 과거 시각 이동 후 완료 처리→기록 골든패스 완주(전이 가드 '시작 후만 완료/노쇼'가 미래 예약을 막으므로). **데모 DB 상태: 예약 #1 completed + 상담 기록 1건(AI 초안) + counselor1 슬롯 토글 흔적 — 리셋은 docker compose down -v 후 재기동**. 브리핑은 배치 잡이 이미 생성한 비식별 콘텐츠(이름 없음) 확인. ⑩ **관리자 대시보드 완료(같은 날, a1dda81·3d41c2c)**: 백엔드 admin/metrics가 dict를 반환해 codegen 타입 공백 → MetricsResponse/ProductCount Pydantic 스키마로 승격(계산 로직·JSON 불변, 테스트 4종 통과) 후 `npm run codegen`으로 타입 유입. 대시보드는 자체 헤더(레이아웃 래퍼 없음), 지표 카드 4종+상태 분해+관심 제품 순위 막대+기간 토글(7/30/90). null 비율은 '—'. 데모 데이터가 completed 1건뿐이라 지표가 단출 — **시드 보정 시 completed/no_show/cancelled 여러 건 + 관심 제품 분포를 넣어야 순위·전환율이 실감남**.

⑪ **실제 바이오컴 관찰(2026-07-10, 시드 보정용 — 사용자 결정: "명칭까지 실제와 일치, 단 대시보드 다음")**: biocom.kr은 iMweb(노코드 커머스) 기반. 로그인은 `POST /ajax/oms/OMS_auth.cm`이 토큰 발급(우리 /auth/login과 동형), 결과지는 로그인 후 `/reportPC`에서만(공개 X — 개인정보라 접근 안 함). 공개 레이어는 커머스+마케팅 위젯(리뷰/채널톡/네이버픽셀)뿐. **공개된 실제 검사 스펙**: ①종합 대사기능 분석 — 소변, 유기산 64종, 6영역(체중조절·항산화·정신건강/집중력·장건강·에너지생성·신체방어), GC-MS/MS. ②음식물 과민증 분석 — 혈액 IgG, 한국인 식품 패널, 반응 등급제. ③영양 중금속 분석 — 모발 0.1g, 미네랄+중금속. (그 외 실서비스: 종합 호르몬 균형, 스트레스 노화, 장내세균, 바이오 펫 영양). **시드 보정 방향**: service_type 3종을 위 실제 명칭/검사법으로, 지표를 유기산·미네랄 계열로, 결과지에 검사법(소변/혈액/모발) 한 줄 표기. 회사명 자체는 레포에 직접 박지 않되(추상화 유지) 검사 도메인 리얼리티는 흡수. 관심 제품도 실제 건강식품 톤(오메가3·프로바이오틱스·비타민D 등)으로.

⑫ **시드 보정 완료(같은 날, a2faf8f)**: seed.py INDICATORS를 실제 스펙으로(유기산 소변/IgG 혈액/모발 미네랄), 프론트 SERVICE_TYPE_LABEL 실제 명칭 동기화 + SERVICE_METHOD(검사법) 신설(결과지 목록 뱃지·상세 히어로 표기). 데모 이력 추가: 과거 상담 8건(완료6·노쇼1·취소1)+기록 6종+관심 제품 분포+오늘 예약 1건+done 브리핑. **시드 확장으로 대시보드 실측: 완료율 66.7%·노쇼율 14.3%(warning)·전환율 66.7%·제품 순위 차등 확인**. 시드는 멱등이라 스펙 재변경 시 docker compose down -v 필요. isOutOfRange 파서가 새 range 형식("150~600" 등) 모두 정상 판정 확인. **주의: 지표 name/range 바꾸면 프론트 판정 칩이 영향받음(파서 3형식 유지할 것)**. ⑬ **노쇼 순화 + 시드 평일 보정(같은 날, c1c6be1)**: StatusBadge에 audience prop — 고객 화면은 '노쇼'→'상담 미진행' + 재예약 CTA(이탈 방지 P3), 상담사/관리자는 지표 용어 유지. seed.py 과거 상담이 주말에 걸리면 직전 평일로 당김. **예약 남용/가족 사칭 방어 확인**: 결과지당 confirmed 1개(uq_confirmed_reservation_per_test_result)+고객 시간겹침 배제(ex_reservations_customer_time_overlap)+슬롯당 active 1개 → 예약 전제가 '돈 낸 결과지'라 무한 스팸 불가. 가족 사칭은 QR 이름+전화 본인확인(403)/로그인 owner 체크(404)로 차단, 단 '가족 동의 검증'은 FR-A4=Won't(의도적 제외). GA/GTM 전환추적은 docs/04 §웹훅에 이미 '2순위 소스'로 문서화(GA는 클라 유실로 원천 부적합, 웹훅이 source of truth). ⑭ **E2E 완료(같은 날, 6a1e096)**: frontend/e2e/ Playwright 12종(`npm run e2e`), 시드 백엔드에 붙음. **E2E가 드러낸 실제 개선 3건 수정**: ①페이지 이동 CTA button+navigate→Link(새탭·스크린리더), ②인증/QR 주제목 CardTitle(div)→asChild h1(CardTitle에 asChild 지원 추가), ③슬롯 오늘 지난 시각 '지난 시간' 비활성(백엔드 과거거부와 일치). **E2E 멱등 규칙: 상태 변경 테스트는 취소로 cleanup(cancelled는 결과지 제약서 빠짐), 예약 테스트는 시드 예약 없는 customer2로 격리(customer1은 오늘예약과 upcoming 정렬 충돌)**. 재시드 없이 반복 통과 확인. ⑮ **docker frontend 완료(같은 날, 1e290ff)**: 멀티스테이지 Dockerfile(node:22-alpine 빌드→nginx:1.27-alpine 서빙), frontend/nginx.conf(/api/→backend:8000 proxy_pass 끝슬래시로 prefix 제거 + try_files SPA fallback + /assets 장기캐시), docker-compose frontend 서비스(8080:80, depends_on backend). **`docker compose up --build` 하나로 3서비스** → 브라우저 http://localhost:8080. 검증: nginx 경유 /api 200, /admin 딥링크 새로고침 SPA fallback, 프로덕션 빌드로 관리자 대시보드 렌더 스크린샷(prod-dashboard.png). 포트맵: db 5433, backend 8000, frontend 8080. ⑯ 다음 시작점: **README** — TL;DR → 1커맨드(`docker compose up --build` → :8080, 시드계정 demo1234) → golden path 서사 → 산출물 6종 매핑표(과제 3)절 1~6 ↔ docs/파일) → 설계 근거 링크. 스크린샷은 스크래치패드 재사용(로그인 login-final, 결과지 r-list2/r-detail2, 예약 c-reserve-*, 상담사 w-today2/w-record-*, 대시보드 prod-dashboard, QR c-consult*). 현재 백엔드 테스트 39종·프론트 빌드/oxlint/E2E 12종 통과, 3서비스 원커맨드 기동 확인. 사용자는 프론트 개발자 — 백엔드 개념은 프론트 비유로. 면접노트는 `interview-notes.local.md` 누적(커밋 금지).

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
