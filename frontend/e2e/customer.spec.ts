import { test, expect } from '@playwright/test'
import { issueConsultToken, login } from './helpers'

test.describe('고객 플로우', () => {
  test('결과지 목록에 본인·가족 결과지가 검사법과 함께 보인다', async ({ page }) => {
    await login(page, 'customer1')
    await expect(page.getByRole('heading', { name: '내 검사 결과' })).toBeVisible()
    await expect(page.getByText('종합 대사기능 분석')).toBeVisible()
    await expect(page.getByText('소변 · 유기산 검사')).toBeVisible()
    // customer1은 가족(김영자) 결과지도 보유 (FR-A2)
    await expect(page.getByText('김영자')).toBeVisible()
  })

  test('결과지 상세에서 지표 판정과 상담 QR을 보여준다', async ({ page }) => {
    await login(page, 'customer1')
    await page.getByText('종합 대사기능 분석').click()
    await expect(page).toHaveURL(/\/results\/\d+$/)
    // 유기산 지표 + 정상/주의 판정 칩
    await expect(page.getByText('8-OHdG (항산화)')).toBeVisible()
    await expect(page.getByText('주의').first()).toBeVisible()
    await expect(page.getByRole('link', { name: '이 결과로 상담 예약하기' })).toBeVisible()
    await expect(page.getByText('전화 상담 예약 QR')).toBeVisible()
  })

  test('예약 생성 → 내 예약 확인 → 취소(정리)', async ({ page }) => {
    // customer2는 시드 확정 예약이 없어 upcoming을 오염 없이 검증할 수 있다
    await login(page, 'customer2')
    await page.getByText('음식물 과민증 분석').click()
    await page.getByRole('link', { name: '이 결과로 상담 예약하기' }).click()
    await expect(page).toHaveURL(/\/reserve/)

    // 시드 슬롯은 내일부터 있으므로, 시간대가 나오는 날짜 칩을 찾아 선택한다
    const days = page.locator('.overflow-x-auto > button')
    let firstTime = page.locator('div.grid button').first()
    for (let i = 1; i < 6; i++) {
      await days.nth(i).click()
      if (await firstTime.isVisible().catch(() => false)) break
    }
    await expect(firstTime).toBeVisible()
    await firstTime.click()
    await page.getByRole('button', { name: /예약하기$/ }).click()
    await expect(page.getByRole('heading', { name: '예약이 확정됐어요' })).toBeVisible()

    // 내 예약에 확정 카드가 뜬다
    await page.getByRole('link', { name: '내 예약 보기' }).click()
    await expect(page).toHaveURL(/\/my\/reservations$/)
    const upcoming = page.locator('section[aria-label="다가오는 상담"]')
    await expect(upcoming.getByText('예약 확정').first()).toBeVisible()

    // 정리: 방금 만든 예약 취소 → 결과지당 예약 제약이 풀려 재실행 가능
    await upcoming.getByRole('button', { name: '취소' }).first().click()
    await page.getByRole('button', { name: '예약 취소' }).click()
    await expect(page.getByRole('button', { name: '예약 취소' })).toHaveCount(0)
  })

  test('QR 진입: 본인확인 성공 시 예약 화면으로, 실패 시 403 안내', async ({ page }) => {
    const token = await issueConsultToken(1) // 결과지 #1 = 이보람 종합 대사기능
    await page.goto(`/consult?t=${token}`)
    await expect(page.getByRole('heading', { name: '본인확인이 필요해요' })).toBeVisible()

    // 오답 → 인라인 에러
    await page.fill('#name', '이보람')
    await page.fill('#phone', '010-0000-0000')
    await page.getByRole('button', { name: '확인하고 예약하기' }).click()
    await expect(page.getByRole('alert')).toContainText('일치하지 않아요')

    // 정답(시드 전화번호) → 스코프 세션으로 예약 화면
    await page.fill('#phone', '010-1000-0001')
    await page.getByRole('button', { name: '확인하고 예약하기' }).click()
    await expect(page).toHaveURL(/\/reserve$/)
    await expect(page.getByText('QR 임시 세션 · 30분 유효')).toBeVisible()
  })

  test('위변조 QR 토큰은 안내 화면을 보여준다', async ({ page }) => {
    await page.goto('/consult?t=tampered-token')
    await expect(page.getByRole('heading', { name: 'QR 코드를 확인할 수 없어요' })).toBeVisible()
  })
})
