# 5. 디자인 시스템 (경량)

프론트엔드 전 화면이 따르는 시각 규칙. 헬스케어·웰니스 도메인에 맞춰 **신뢰감 있는 딥 그린 + 클린한 화이트 여백** 톤으로 통일한다. 구현은 Tailwind `@theme` + shadcn/ui 테마 변수에 아래 토큰을 매핑하는 방식 — shadcn 기본 팔레트는 사용하지 않으며, 토큰 밖 임의 색상은 금지 (기술 구조는 `06-frontend-design.md` §6.1).

## 5.1 컬러 토큰

```css
:root {
  /* Brand */
  --color-primary:        #16B3AC;  /* 틸 민트 — CTA, 활성 상태, 링크 */
  --color-primary-dark:   #1D8D88;  /* hover/pressed */
  --color-primary-soft:   #E8F7F6;  /* 선택 배경, 뱃지 배경 */
  --color-deep:           #0E282B;  /* 딥 틸 그린 — 헤더, 히어로, 강조 배경 */

  /* Neutral */
  --color-text:           #222222;
  --color-text-secondary: #8C8C8C;
  --color-border:         #EEEEEE;
  --color-surface:        #F4F4F4;  /* 카드·섹션 배경 */
  --color-bg:             #FFFFFF;

  /* Semantic (예약 상태·알림) */
  --color-success:        #1D8D88;  /* completed */
  --color-info:           #16B3AC;  /* confirmed */
  --color-warning:        #E8A23D;  /* no_show, 임박 리마인더 */
  --color-danger:         #D64545;  /* cancelled, 삭제 액션 */
}
```

- 예약 상태 뱃지 매핑: `confirmed`=info, `completed`=success, `no_show`=warning, `cancelled`=neutral(회색) — 취소는 오류가 아니므로 danger를 쓰지 않는다. danger는 파괴적 액션(삭제 확인)에만.
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
| 고객 (결과지·QR·예약) | 화이트 배경 + primary CTA, 여백 넉넉히. 딥 그린은 헤더/히어로만 | 건강정보를 보는 화면 — 안심·신뢰가 우선 |
| 상담사 워크스페이스 | 밀도 높은 리스트/카드, surface 배경 위 화이트 카드. 완료/노쇼 등 상태 액션 버튼 상시 노출 | 하루 여러 건 처리하는 업무 화면 — 스캔 속도 우선 |
| 관리자 대시보드 | 지표 카드 4개(건수·완료율·노쇼율·전환율) + 차트. 색은 primary·neutral·warning 3계열로 제한 | 숫자가 주인공, 장식 최소화 |

## 5.5 원칙

1. 색은 위 토큰만 사용 — 임의 hex 추가 금지
2. primary는 화면당 주요 액션 1개에만 (버튼 남발 금지)
3. 상태는 색+텍스트 병행 표기 (색맹 대비, 예: 뱃지에 "노쇼" 라벨 필수)
4. 로딩·빈 상태·에러 상태를 모든 목록 화면에 정의 (특히 슬롯 만석 시 대안 안내가 빈 화면을 대체)
