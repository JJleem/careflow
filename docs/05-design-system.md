# 5. 디자인 시스템 (경량)

프론트엔드 전 화면이 따르는 시각 규칙. 과제의 바이오컴은 실제 `(주)알로스타` 운영 브랜드이므로, `https://biocom.kr/`의 브랜드 톤을 기준으로 **바이오컴 민트 + 뉴트럴 그레이 + 클린한 화이트 여백**으로 통일한다. 구현은 Tailwind `@theme` + shadcn/ui 테마 변수에 아래 토큰을 매핑하는 방식 — shadcn 기본 팔레트는 사용하지 않으며, 토큰 밖 임의 색상은 금지 (기술 구조는 `06-frontend-design.md` §6.1).

브랜드 관찰(2026-07-09): 공식 사이트는 로고의 민트/그레이, `energy giver` 태그라인, `민트패밀리 멤버십`, 분석서비스·건강식품·관리 프로그램 중심의 커머스 톤을 사용한다. 따라서 고객 화면은 실제 사이트와 이어지는 밝은 민트 CTA를 쓰고, 상담사/관리자 화면은 운영 도구답게 같은 민트를 절제된 포커스 색으로만 사용한다.

## 5.1 컬러 토큰

```css
:root {
  /* Brand */
  --color-brand-mint:     #22BDB8;  /* 바이오컴 로고 민트 — 브랜드 포인트, info */
  --color-primary:        #087D78;  /* 접근성 보정 민트 — CTA, 활성 상태, 링크 */
  --color-primary-dark:   #066A66;  /* hover/pressed */
  --color-primary-soft:   #E9FAF8;  /* 선택 배경, 뱃지 배경 */
  --color-deep:           #0B2A2B;  /* 민트가 떠 보이는 딥 틸 — 헤더, 강조 배경 */

  /* Neutral */
  --color-text:           #1F2424;
  --color-text-secondary: #8A8D8E;  /* 로고 그레이 계열 */
  --color-border:         #E8ECEB;
  --color-surface:        #F7F8F7;  /* 카드·섹션 배경 */
  --color-bg:             #FFFFFF;

  /* Semantic (예약 상태·알림) */
  --color-success:        #087D78;  /* completed */
  --color-info:           #22BDB8;  /* confirmed */
  --color-warning:        #E4A13A;  /* no_show, 임박 리마인더 */
  --color-danger:         #D94E4E;  /* cancelled, 삭제 액션 */
}
```

- 예약 상태 뱃지 매핑: `confirmed`=info, `completed`=success, `no_show`=warning, `cancelled`=neutral(회색) — 취소는 오류가 아니므로 danger를 쓰지 않는다. danger는 파괴적 액션(삭제 확인)에만.
- `--color-brand-mint`는 로고/정보성 포인트에 쓰고, 흰 글자가 올라가는 CTA는 대비 확보를 위해 `--color-primary`를 사용한다.
- 대시보드 차트: primary 계열 단색 + neutral로 절제. 노쇼율 등 경고성 지표만 warning.

## 5.2 타이포그래피

- 폰트: `Pretendard, -apple-system, "Apple SD Gothic Neo", "Noto Sans KR", sans-serif` (CDN 없이 로컬/시스템 폴백 허용)
- 스케일: 28/22/18(제목), 15(본문), 13(보조). 숫자 지표(대시보드 카드)는 32 bold
- 결과지 지표 수치는 tabular-nums로 정렬

## 5.3 형태·간격

- Radius: 버튼·인풋 `4px`, 카드 `10px`, 모달·시트 `20px`, 뱃지·필 `100px`
- 간격: 4px 배수 스케일 (4/8/12/16/24/32)
- 그림자: 카드 `0 1px 3px rgba(0,0,0,.06)`, 모달 `0 8px 24px rgba(0,0,0,.16)` — 두 단계만
- 테두리는 `--color-border` 1px, 구분은 여백 우선

## 5.4 화면별 톤

| 영역 | 톤 | 이유 |
|------|-----|------|
| 고객 (결과지·QR·예약) | 공식몰과 이어지는 화이트 배경 + 민트 CTA, 여백 넉넉히. 딥 틸은 상단 헤더/결과 요약 강조에만 | 건강정보를 보는 화면 — 실제 바이오컴 브랜드와 안심감이 우선 |
| 상담사 워크스페이스 | 밀도 높은 리스트/카드, surface 배경 위 화이트 카드. 민트는 선택·확정·저장에만 사용하고 완료/노쇼 등 상태 액션 버튼 상시 노출 | 하루 여러 건 처리하는 업무 화면 — 브랜드는 유지하되 스캔 속도 우선 |
| 관리자 대시보드 | 지표 카드 4개(건수·완료율·노쇼율·전환율) + 차트. 색은 primary·neutral·warning 3계열로 제한 | 숫자가 주인공, 장식 최소화 |

## 5.5 원칙

1. 색은 위 토큰만 사용 — 임의 hex 추가 금지
2. primary는 화면당 주요 액션 1개에만 (버튼 남발 금지)
3. 상태는 색+텍스트 병행 표기 (색맹 대비, 예: 뱃지에 "노쇼" 라벨 필수)
4. 로딩·빈 상태·에러 상태를 모든 목록 화면에 정의 (특히 슬롯 만석 시 대안 안내가 빈 화면을 대체)
