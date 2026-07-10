import { test, expect } from '@playwright/test'
import { login } from './helpers'

test.describe('상담사 워크스페이스', () => {
  test('오늘 일정에 예약과 AI 브리핑이 보인다', async ({ page }) => {
    await login(page, 'counselor1')
    await expect(page.getByRole('heading', { name: '오늘 일정' })).toBeVisible()
    // 시드된 오늘 예약 + done 브리핑
    await expect(page.getByText('AI 사전 브리핑')).toBeVisible()
    await expect(page.getByText('종합 대사기능 분석')).toBeVisible()
    await expect(page.getByRole('button', { name: '완료 처리' })).toBeVisible()
  })

  test('슬롯 관리에서 빈 시간을 열고 닫을 수 있다', async ({ page }) => {
    await login(page, 'counselor1')
    await page.goto('/work/slots')
    await expect(page.getByRole('heading', { name: '슬롯 관리' })).toBeVisible()
    // 오늘의 지난 시각은 열 수 없으므로, 미래인 다음 평일 칩을 선택한다
    const days = page.locator('.overflow-x-auto > button')
    for (let i = 1; i < 6; i++) {
      await days.nth(i).click()
      const slot = page.getByRole('button', { name: /^09:00/ })
      if ((await slot.textContent())?.includes('닫힘')) {
        // 09:00은 시드 슬롯(10~16시)에 없어 '닫힘' — 토글로 열고 다시 닫는다
        await slot.click()
        await expect(slot).toContainText('열림')
        await slot.click()
        await expect(slot).toContainText('닫힘')
        return
      }
    }
    throw new Error('열 수 있는 09:00 슬롯을 가진 평일을 찾지 못함')
  })
})

test.describe('관리자 대시보드', () => {
  test('운영 지표 카드와 관심 제품 순위가 보인다', async ({ page }) => {
    await login(page, 'admin')
    await expect(page.getByRole('heading', { name: '운영 지표' })).toBeVisible()
    await expect(page.getByText('완료율')).toBeVisible()
    await expect(page.getByText('노쇼율')).toBeVisible()
    await expect(page.getByText('구매 전환율')).toBeVisible()
    // 시드 이력 기반 관심 제품 순위 (오메가3가 최다)
    await expect(page.getByRole('heading', { name: '관심 제품 순위' })).toBeVisible()
    await expect(page.getByText('오메가3')).toBeVisible()
  })
})
