import { defineConfig, devices } from '@playwright/test';

const baseURL = process.env.BASE_URL ?? 'https://staging-pda.up.railway.app';

export default defineConfig({
  testDir: './staging-smoke',
  fullyParallel: false,
  workers: 1,
  timeout: 180_000,
  reporter: 'list',
  use: {
    baseURL,
    trace: 'retain-on-failure',
    ...devices['Desktop Chrome'],
  },
});
