import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: "http://localhost:9009",
  },
  webServer: {
    command: "env DEEPSEEK_API_KEY= NINE_BARS_DEEPSEEK_API_KEY= uv run nine-bars",
    cwd: "..",
    url: "http://localhost:9009/healthz",
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
