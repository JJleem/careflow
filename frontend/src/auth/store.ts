import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { components } from '../api/schema'

export type AuthUser = components['schemas']['UserResponse']
export type Role = AuthUser['role']

interface AuthState {
  token: string | null
  user: AuthUser | null
  login: (token: string, user: AuthUser) => void
  logout: () => void
}

// 정식 JWT는 localStorage 유지 — 새로고침 생존 (docs/06 §6.4, XSS 리스크는 MVP 수용)
export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      login: (token, user) => set({ token, user }),
      logout: () => set({ token: null, user: null }),
    }),
    { name: 'cf.auth' },
  ),
)

// 로그인 성공·역할 불일치 시 보내는 역할별 홈 (docs/06 §6.3)
export const roleHome: Record<Role, string> = {
  customer: '/results',
  counselor: '/work/today',
  admin: '/admin',
}
