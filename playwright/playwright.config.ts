import { defineConfig, devices } from '@playwright/test';

/**
 * QAZen S6 runner config. Specs are compiled into playwright/generated/<run_id>/.
 * Orchestrator sets QAZEN_SPEC_DIR / QAZEN_OUTPUT_DIR / QAZEN_BASE_URL via env.
 */
const specDir = process.env.QAZEN_SPEC_DIR || './generated';
const outputDir = process.env.QAZEN_OUTPUT_DIR || './test-results';
const baseURL = process.env.QAZEN_BASE_URL || 'https://www.saucedemo.com';
const headed =
  (process.env.S6_HEADED || '').toLowerCase() === 'true' ||
  (process.env.S6_HEADED || '') === '1' ||
  (process.env.S6_HEADED || '').toLowerCase() === 'yes';
const slowMo = Number(process.env.S6_SLOW_MO_MS || 0);

export default defineConfig({
  testDir: specDir,
  outputDir,
  timeout: 90_000,
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: Number(process.env.QAZEN_RETRIES || 0),
  workers: 1,
  reporter: [
    ['list'],
    ['json', { outputFile: process.env.QAZEN_JSON_REPORT || `${outputDir}/report.json` }],
  ],
  use: {
    baseURL,
    headless: !headed,
    ...(Number.isFinite(slowMo) && slowMo > 0 ? { slowMo } : {}),
    viewport: { width: 1920, height: 1080 },
    actionTimeout: 30_000,
    navigationTimeout: 60_000,
    screenshot: 'on',
    video: 'retain-on-failure',
    trace: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
