// QR 스코프 토큰 — 30분 TTL "임시 출입증". sessionStorage라 탭을 닫으면 소멸하고,
// 정식 JWT(localStorage)와 키를 분리해 상호 오염을 차단한다 (docs/06 §6.4).
const KEY = 'cf.scoped'

export interface ScopedSession {
  token: string
  testResultId: number
  subjectId: number
}

export function getScopedSession(): ScopedSession | null {
  const raw = sessionStorage.getItem(KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as ScopedSession
  } catch {
    sessionStorage.removeItem(KEY)
    return null
  }
}

export function setScopedSession(session: ScopedSession) {
  sessionStorage.setItem(KEY, JSON.stringify(session))
}

export function clearScopedSession() {
  sessionStorage.removeItem(KEY)
}
