import { defineConfig, devices } from '@playwright/test'

// E2E는 시드된 백엔드(docker compose up + 시드)에 붙는다. 골든 패스 테스트는
// 생성한 예약을 취소로 정리해 반복 실행 가능하지만, 읽기 지표는 fresh 시드를 가정한다.
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false, // 공유 시드 데이터를 건드리므로 순차 실행
  workers: 1,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  // 백엔드(:8000)는 docker로 미리 띄운다. 프론트 dev 서버만 자동 기동.
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: true,
    timeout: 60_000,
  },
})
