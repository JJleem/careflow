// 서버는 UTC로 주고받고, 표시 직전에만 Asia/Seoul로 변환한다 (NFR-8, docs/06 §6.7)
const TZ = 'Asia/Seoul'

export function formatDate(iso: string) {
  return new Intl.DateTimeFormat('ko-KR', {
    timeZone: TZ,
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'short',
  }).format(new Date(iso))
}

export function formatTime(iso: string) {
  return new Intl.DateTimeFormat('ko-KR', {
    timeZone: TZ,
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(new Date(iso))
}

export function formatDateTime(iso: string) {
  return `${formatDate(iso)} ${formatTime(iso)}`
}

/** KST 기준 YYYY-MM-DD (API date 쿼리 파라미터용) */
export function toDateParam(d: Date) {
  return new Intl.DateTimeFormat('en-CA', { timeZone: TZ }).format(d)
}

/** 오늘부터 n일치 날짜 칩 데이터 (KST 기준) */
export function upcomingDays(n: number) {
  return Array.from({ length: n }, (_, i) => {
    const d = new Date(Date.now() + i * 86_400_000)
    return {
      value: toDateParam(d),
      day: new Intl.DateTimeFormat('ko-KR', { timeZone: TZ, day: 'numeric' }).format(d),
      weekday: new Intl.DateTimeFormat('ko-KR', { timeZone: TZ, weekday: 'short' }).format(d),
      month: new Intl.DateTimeFormat('ko-KR', { timeZone: TZ, month: 'numeric' }).format(d),
    }
  })
}

/** "YYYY-MM-DD" → "7월 15일 (수)" — 시간 정보 없는 date 문자열용 */
export function formatDateOnly(dateStr: string) {
  return new Intl.DateTimeFormat('ko-KR', {
    timeZone: TZ,
    month: 'long',
    day: 'numeric',
    weekday: 'short',
  }).format(new Date(`${dateStr}T00:00:00+09:00`))
}
