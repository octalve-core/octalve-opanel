import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './e2e', workers: 1,
  use: { baseURL: 'http://127.0.0.1:3300', trace: 'retain-on-failure' },
  webServer: {command:'node node_modules/next/dist/bin/next start -H 127.0.0.1 -p 3300',
    url:'http://127.0.0.1:3300',reuseExistingServer:false},
});
