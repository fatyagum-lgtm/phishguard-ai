import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30000,
  workers: 1,
  use: {
    baseURL: 'http://127.0.0.1:8000',
    headless: true,
    viewport: { width: 1440, height: 1050 },
  },
  reporter: 'list',
  webServer: {
    command: 'python -m phishguard.cli serve',
    cwd: '..',
    url: 'http://127.0.0.1:8000/api/health',
    reuseExistingServer: !process.env.CI,
    timeout: 30000,
  },
});
