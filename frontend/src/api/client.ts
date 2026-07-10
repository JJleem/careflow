import createClient, { type Middleware } from 'openapi-fetch'
import type { paths } from './schema'
import { useAuthStore } from '../auth/store'
import { clearScopedSession, getScopedSession } from '../auth/scopedSession'

const authMiddleware: Middleware = {
  onRequest({ request }) {
    // QR 플로우 중이면 스코프 토큰 우선, 없으면 정식 JWT (docs/06 §6.4)
    const token = getScopedSession()?.token ?? useAuthStore.getState().token
    if (token) request.headers.set('Authorization', `Bearer ${token}`)
    return request
  },
  onResponse({ request, response }) {
    // 401 = 토큰 만료·무효 → 세션 정리 후 로그인으로.
    // 단 /auth/* 자체의 401(자격 증명 오류)은 화면에서 인라인 처리한다.
    if (response.status === 401 && !new URL(request.url).pathname.startsWith('/api/auth/')) {
      clearScopedSession()
      useAuthStore.getState().logout()
      if (window.location.pathname !== '/login') window.location.assign('/login')
    }
    return response
  },
}

export const api = createClient<paths>({ baseUrl: '/api' })
api.use(authMiddleware)
