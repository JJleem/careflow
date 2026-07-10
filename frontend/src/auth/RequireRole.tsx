import { Navigate, Outlet } from 'react-router-dom'
import { roleHome, useAuthStore, type Role } from './store'
import { getScopedSession } from './scopedSession'

// 백엔드 require_roles의 프론트 쌍 — UX 장치일 뿐, 최종 방어선은 백엔드 403 (docs/06 §6.3)
export default function RequireRole({
  roles,
  allowScopedSession = false,
}: {
  roles: Role[]
  allowScopedSession?: boolean
}) {
  const user = useAuthStore((s) => s.user)
  // /reserve는 QR 스코프 세션으로도 진입 가능 (docs/06 §6.3 "고객 · 스코프 세션")
  if (allowScopedSession && getScopedSession()) return <Outlet />
  if (!user) return <Navigate to="/login" replace />
  if (!roles.includes(user.role)) return <Navigate to={roleHome[user.role]} replace />
  return <Outlet />
}
