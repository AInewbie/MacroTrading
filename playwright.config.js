import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./test/browser",
  timeout: 60000,
  workers: 1,
  retries: 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: { screenshot: "only-on-failure", trace: "retain-on-failure" },
  webServer: [4173, 4174].map((port) => ({
    command: `python3 scripts/qa_server.py --port ${port}`,
    url: `http://127.0.0.1:${port}/api/health`,
    reuseExistingServer: false,
    timeout: 30000,
  })),
  projects: [
    {
      name: "desktop",
      use: { ...devices["Desktop Chrome"], baseURL: "http://127.0.0.1:4173" },
    },
    {
      name: "mobile",
      use: { ...devices["Pixel 7"], baseURL: "http://127.0.0.1:4174" },
    },
  ],
});
