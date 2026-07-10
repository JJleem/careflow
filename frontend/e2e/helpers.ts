import { expect, type Page } from '@playwright/test'

// 시드 계정 (backend/seed.py) — 전 계정 공통 비밀번호
export const PASSWORD = 'demo1234'
export const ACCOUNTS = {
  admin: 'admin@careflow.kr',
  counselor1: 'counselor1@careflow.kr',
  customer1: 'customer1@careflow.kr',
  customer2: 'customer2@careflow.kr',
} as const

export const ROLE_HOME = {
  admin: '/admin',
  counselor1: '/work/today',
  customer1: '/results',
  customer2: '/results',
} as const

export async function login(page: Page, account: keyof typeof ACCOUNTS) {
  await page.goto('/login')
  await page.fill('#email', ACCOUNTS[account])
  await page.fill('#password', PASSWORD)
  await Promise.all([
    page.waitForURL(`**${ROLE_HOME[account]}`),
    page.getByRole('button', { name: '로그인' }).click(),
  ])
}

/** 로그인 없이 QR 상담 토큰을 발급받는다(정식 고객 인증으로) — QR 진입 플로우 테스트용 */
export async function issueConsultToken(testResultId: number): Promise<string> {
  const base = 'http://localhost:8000'
  const login = await fetch(`${base}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: ACCOUNTS.customer1, password: PASSWORD }),
  }).then((r) => r.json())
  const tok = await fetch(`${base}/test-results/${testResultId}/consult-token`, {
    headers: { Authorization: `Bearer ${login.access_token}` },
  }).then((r) => r.json())
  return tok.token as string
}

export { expect }
