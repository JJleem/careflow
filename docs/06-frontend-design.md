# 6. 프론트엔드 설계 (경량)

React 18 + TypeScript + Vite. 시각 규칙은 `05-design-system.md`, 화면 목록은 `04 §4.8`을 따르고, 이 문서는 **기술 구조**(라우팅·상태·API 계층·세션)를 정의한다.

## 6.1 라이브러리 선택과 근거

| 영역 | 선택 | 근거 |
|------|------|------|
| 라우팅 | react-router-dom | 표준. 역할별 레이아웃 라우트 + 가드 |
| 서버 상태 | TanStack Query | 이 앱 상태의 대부분이 서버 데이터의 캐시(슬롯·예약·알림·지표). 캐싱·재검증·로딩/에러 상태를 선언적으로. **Redux류 미도입** — 전역 클라이언트 상태는 인증뿐이라 Context 하나로 충분 |
| API 타입 | openapi-typescript | FastAPI의 `/openapi.json` → TS 타입 자동 생성. 백엔드 스키마 변경 시 프론트가 **빌드 타임에 깨져** 타입 드리프트를 차단. 수동 타입 중복 관리 제거 |
| QR 렌더 | qrcode.react | 결과지 상세의 상담 QR(서명 딥링크의 시각화). 클라이언트 렌더 — 외부 서비스 불필요 |
| 스타일 | CSS 변수 + CSS Modules | docs/05 토큰을 `tokens.css` 하나로. MVP에 컴포넌트 라이브러리·Tailwind는 과설계 (05 §전제) |
| 폼 | 제어 컴포넌트 (라이브러리 없음) | 폼이 3개(로그인·가입·QR 검증)뿐. react-hook-form은 규모 대비 과함 |

## 6.2 디렉터리 구조

```
frontend/src/
├── api/
│   ├── client.ts          # fetch 래퍼: baseURL, 토큰 주입, 401/403 공통 처리
│   ├── schema.d.ts        # openapi-typescript 생성물 (수정 금지, npm run codegen)
│   └── queries/           # TanStack Query 훅 (useSlots, useMyReservations, ...)
├── auth/
│   ├── AuthContext.tsx     # user + token, login/logout
│   ├── RequireRole.tsx     # 역할 가드 라우트 (백엔드 require_roles의 프론트 쌍)
│   └── scopedSession.ts    # QR 스코프 토큰 (sessionStorage, 정식 토큰과 격리)
├── features/
│   ├── customer/          # 결과지 목록/상세(QR), 예약, 내 예약, 알림함
│   ├── consult/           # QR 진입: 검증 → 프리셀렉트 예약 (공개 라우트)
│   ├── counselor/         # 당일 일정(브리핑), 기록 작성(AI 구조화), 슬롯 관리
│   └── admin/             # 대시보드 (지표 카드 + 관심 제품 순위)
├── components/            # Badge, Card, EmptyState, Spinner 등 공용
├── styles/tokens.css      # docs/05 컬러·타이포·간격 토큰 (임의 색상 금지)
└── App.tsx                # 라우터 + Provider 배선
```

기능(feature) 기준 분할 — 화면 단위 작업·리뷰가 쉽고, 역할별 코드 경계가 백엔드 RBAC 경계와 일치한다.

## 6.3 라우팅 맵

| 경로 | 화면 | 접근 |
|------|------|------|
| `/login`, `/signup` | 로그인/가입 | 공개 |
| `/consult?t=` | QR 검증 → 프리셀렉트 예약 | 공개 (스코프 세션) |
| `/results`, `/results/:id` | 결과지 목록/상세(지표 + 상담 QR) | 고객 |
| `/reserve` | 날짜→시간대 예약 (만석 시 대안) | 고객 · 스코프 세션 |
| `/my/reservations`, `/notifications` | 내 예약 / 알림함 | 고객 |
| `/work/today` | 당일 일정 + LLM 브리핑 + 완료/노쇼 | 상담사 |
| `/work/records/:reservationId` | 메모 → AI 구조화 → 검수 저장 | 상담사 |
| `/work/slots` | 주간 슬롯 등록/삭제 | 상담사 |
| `/admin` | 지표 대시보드 | 관리자 |

- 로그인 성공 시 역할별 홈으로 리다이렉트: customer→`/results`, counselor→`/work/today`, admin→`/admin`.
- `RequireRole`이 미인증→`/login`, 역할 불일치→역할 홈으로 보낸다. 백엔드가 최종 방어선(403)이고 프론트 가드는 UX 장치 — 보안을 프론트에 의존하지 않는다.

## 6.4 인증·세션 전략

| 토큰 | 저장 | 근거 |
|------|------|------|
| 정식 JWT | localStorage | 새로고침 유지 필요. MVP 수용 리스크: XSS 시 탈취 가능 — 실운영은 httpOnly 쿠키 + CSRF 토큰으로 전환(백엔드 어댑터 지점) |
| QR 스코프 토큰 | sessionStorage | 탭 닫으면 소멸 — 30분 TTL "임시 출입증" 성격과 일치. 정식 토큰과 키 분리로 상호 오염 차단 |

- `client.ts`는 요청 시점에 **스코프 토큰이 있으면 우선 사용**(QR 플로우 중), 없으면 정식 토큰.
- 401 응답 → 토큰 폐기 후 `/login`. 스코프 세션의 403("QR 세션으로는 접근 불가") → 로그인 유도 화면.

## 6.5 서버 상태 규칙 (TanStack Query)

- 쿼리 키는 리소스 경로 그대로: `['slots', date]`, `['me','reservations']`, `['admin','metrics',from,to]`.
- 뮤테이션 후 관련 키 무효화: 예약 생성 → `slots`·`me/reservations` 무효화, 상태 전이 → 동일 + `notifications`.
- 409(만석·중복)는 에러가 아니라 **분기 응답**으로 다룬다: 만석 409의 `alternative_times/dates`를 그대로 대안 UI로 렌더 (05 §5.5-4 "만석 시 대안 안내가 빈 화면을 대체").
- 알림함은 30초 refetchInterval (인앱 채널의 수신 폴링 — 백엔드 발송 주기 60초와 짝).

## 6.6 백엔드 연동

- dev: Vite `server.proxy`로 `/api` → `http://localhost:8000` (CORS 회피, 쿠키 전환 대비). 백엔드에 `/api` prefix가 없으므로 프록시에서 rewrite.
- docker: frontend 컨테이너(nginx serve)에서 동일 프록시 규칙. `docker compose up` 하나로 3서비스 (NFR-6).
- 타입 생성: `npm run codegen` → 백엔드 `/openapi.json` fetch → `api/schema.d.ts`. CI 없는 MVP에서는 커밋된 생성물을 쓰고, 변경 시 재생성을 컨벤션으로.

## 6.7 상태·표시 규칙 (05와의 접점)

- 예약 상태 뱃지는 05 §5.1 시맨틱 매핑 고정: confirmed=info, completed=success, no_show=warning, cancelled=neutral.
- 시각 표시: 서버는 UTC로 주고받고 **표시 직전에만 Asia/Seoul 변환** (`Intl.DateTimeFormat('ko-KR', {timeZone:'Asia/Seoul'})`) — NFR-8의 프론트 절반.
- 모든 목록 화면은 로딩(스켈레톤)·빈 상태(EmptyState)·에러(재시도 버튼) 3종을 의무 구현 (05 §5.5-4).
- 지표 수치는 `tabular-nums`, 비율 null(0건 기간)은 "—"로 표시 (0%와 구분).
