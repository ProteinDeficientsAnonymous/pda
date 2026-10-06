import { defineConfig, devices } from '@playwright/test';

const port = process.env.VISUAL_PORT ?? '3000';

export default defineConfig({
  testDir: './visual',
  // Vitest files (*.test.ts) live next to the specs. Playwright's default
  // match includes them, and loading one crashes outside Vitest.
  testMatch: '**/*.spec.ts',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  reporter: 'list',
  // Vite only. Logged-in shots need uvicorn already listening on port 8000.
  webServer: {
    command: `pnpm dev --host 127.0.0.1 --port ${port}`,
    url: `http://127.0.0.1:${port}`,
    reuseExistingServer: !process.env.CI,
  },
  use: {
    ...devices['Desktop Chrome'],
    baseURL: `http://127.0.0.1:${port}`,
    viewport: { width: 1280, height: 800 },
    locale: 'en-US',
    timezoneId: 'America/New_York',
  },
});
