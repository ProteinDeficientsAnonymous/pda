import { defineConfig, devices } from '@playwright/test';

const port = process.env.PROD_SMOKE_PORT ?? '8103';

export default defineConfig({
  testDir: './e2e-prod',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI
    ? [['dot'], ['html', { outputFolder: 'playwright-report', open: 'never' }]]
    : 'list',
  use: {
    ...devices['Desktop Chrome'],
    baseURL: `http://127.0.0.1:${port}`,
    trace: 'on-first-retry',
  },
});
