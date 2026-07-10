import { test, expect } from '@playwright/test'
import { ACCOUNTS, login } from './helpers'

test.describe('인증·역할 라우팅', () => {
  test('역할별로 홈으로 리다이렉트된다', async ({ page }) => {
    await login(page, 'customer1')
    await expect(page).toHaveURL(/\/results$/)
    await login(page, 'counselor1')
    await expect(page).toHaveURL(/\/work\/today$/)
    await login(page, 'admin')
    await expect(page).toHaveURL(/\/admin$/)
  })

  test('비밀번호가 틀리면 인라인 에러를 보여준다', async ({ page }) => {
    await page.goto('/login')
    await page.fill('#email', ACCOUNTS.customer1)
    await page.fill('#password', 'wrong-password')
    await page.getByRole('button', { name: '로그인' }).click()
    await expect(page.getByRole('alert')).toContainText('비밀번호')
    await expect(page).toHaveURL(/\/login$/)
  })

  test('미인증 상태로 보호 라우트 접근 시 로그인으로 보낸다', async ({ page }) => {
    await page.goto('/work/today')
    await expect(page).toHaveURL(/\/login$/)
  })

  test('역할이 다른 라우트 접근 시 자기 역할 홈으로 보낸다', async ({ page }) => {
    await login(page, 'customer1')
    await page.goto('/admin') // 고객이 관리자 페이지 접근
    await expect(page).toHaveURL(/\/results$/)
  })
})
