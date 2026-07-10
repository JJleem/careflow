import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../auth/store'
import Logo from './Logo'
import { cn } from '@/lib/utils'

const NAV = [
  { to: '/work/today', label: '오늘 일정' },
  { to: '/work/slots', label: '슬롯 관리' },
] as const

// 상담사 워크스페이스 틀 — 하루 여러 건을 처리하는 업무 화면이라 고객 화면보다 넓은 컬럼 (05 §5.4)
export default function WorkLayout() {
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)

  return (
    <div className="min-h-screen bg-surface">
      <header className="sticky top-0 z-10 bg-bg/90 backdrop-blur">
        <div className="mx-auto flex h-14 w-full max-w-2xl items-center gap-5 px-4">
          <Link to="/work/today">
            <Logo />
          </Link>
          <span className="rounded-pill bg-surface px-2 py-0.5 text-caption font-semibold text-text-secondary">
            상담사
          </span>
          <nav className="flex gap-4">
            {NAV.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  cn(
                    'text-body transition-colors',
                    isActive ? 'font-bold text-text' : 'text-text-secondary hover:text-text',
                  )
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-3">
            <span className="text-caption text-text-secondary">{user?.name}</span>
            <button
              type="button"
              onClick={() => {
                logout()
                navigate('/login')
              }}
              className="text-caption text-text-secondary transition-colors hover:text-text"
            >
              로그아웃
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-2xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
