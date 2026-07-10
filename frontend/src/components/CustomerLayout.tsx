import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../auth/store'
import { getScopedSession, clearScopedSession } from '../auth/scopedSession'
import { useNotifications } from '../api/queries/notifications'
import Logo from './Logo'
import { cn } from '@/lib/utils'

const NAV = [
  { to: '/results', label: '결과지' },
  { to: '/my/reservations', label: '내 예약' },
  { to: '/notifications', label: '알림' },
] as const

// 고객 화면 공용 틀 — surface 캔버스 + 흰 헤더, 콘텐츠는 모바일 우선 좁은 컬럼 (05 §5.4)
// QR 스코프 세션(user 없음)에서는 내비 없이 임시 세션 안내만 노출한다.
export default function CustomerLayout() {
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)
  const scoped = !user && getScopedSession() !== null
  const { data: notifications } = useNotifications(!!user)
  const unread = notifications?.filter((n) => !n.read).length ?? 0

  return (
    <div className="min-h-screen bg-surface">
      <header className="sticky top-0 z-10 bg-bg/90 backdrop-blur">
        <div className="mx-auto flex h-14 w-full max-w-xl items-center gap-5 px-4">
          <Link to={user ? '/results' : '/login'}>
            <Logo />
          </Link>
          {user && (
            <>
              <nav className="flex gap-4">
                {NAV.map(({ to, label }) => (
                  <NavLink
                    key={to}
                    to={to}
                    className={({ isActive }) =>
                      cn(
                        'relative text-body transition-colors',
                        isActive ? 'font-bold text-text' : 'text-text-secondary hover:text-text',
                      )
                    }
                  >
                    {label}
                    {to === '/notifications' && unread > 0 && (
                      <span className="absolute -top-0.5 -right-2 size-1.5 rounded-pill bg-danger" aria-label={`읽지 않은 알림 ${unread}건`} />
                    )}
                  </NavLink>
                ))}
              </nav>
              <button
                type="button"
                onClick={() => {
                  logout()
                  clearScopedSession()
                  navigate('/login')
                }}
                className="ml-auto text-caption text-text-secondary transition-colors hover:text-text"
              >
                로그아웃
              </button>
            </>
          )}
          {scoped && <span className="ml-auto text-caption text-text-secondary">QR 임시 세션 · 30분 유효</span>}
        </div>
      </header>
      <main className="mx-auto w-full max-w-xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
