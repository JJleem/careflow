/** FastAPI 에러 응답(detail: string | object)을 상태 코드와 함께 보존 —
 *  409 만석 응답처럼 "에러가 아니라 분기 응답"인 경우 detail을 UI 데이터로 쓴다 (docs/06 §6.5) */
export class ApiError extends Error {
  status: number
  detail: unknown

  constructor(status: number, detail: unknown) {
    super(typeof detail === 'string' ? detail : `HTTP ${status}`)
    this.status = status
    this.detail = detail
  }
}

/** openapi-fetch 결과에서 ApiError 생성 — 에러 스키마 미선언 엔드포인트(error: never)도 수용 */
export function apiError(response: Response, error: unknown): ApiError {
  const detail = (error as { detail?: unknown } | null | undefined)?.detail
  return new ApiError(response.status, detail ?? error)
}

export function detailMessage(err: unknown, fallback: string): string {
  if (err instanceof ApiError && typeof err.detail === 'string') return err.detail
  return fallback
}
