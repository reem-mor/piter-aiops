import { test, expect, type Page } from "@playwright/test";

const baseURL = process.env.PITER_BASE_URL || "http://127.0.0.1:8080";
const UI_VERSION = "demo-polish-v6";

const DEMO_QUESTIONS = [
  "What's the last P1 alert?",
  "Which service is the noisiest?",
  "What was the last deployment?",
  "Who is the data engineer on call today?",
  "What are the latest 3 incidents?",
] as const;

async function requireDemoPolishUi(page: Page): Promise<void> {
  const marker = page.locator(`.app-shell[data-ui-version="${UI_VERSION}"]`);
  const hasMarker = await marker.isVisible().catch(() => false);
  test.skip(
    !hasMarker,
    `Built ${UI_VERSION} SPA not served — run: cd frontend && npm run build, then restart Flask on ${baseURL}`,
  );
}

async function clickStartAlertStream(page: Page): Promise<void> {
  const startBtn = page.locator(".top-bar-actions button.btn-primary", {
    hasText: /start alert stream/i,
  });
  await expect(startBtn).toBeVisible({ timeout: 10_000 });
  await startBtn.click();
}

test.describe("PITER Ops demo path", () => {
  test.beforeEach(async ({ request }) => {
    try {
      const res = await request.get(`${baseURL}/api/health`);
      test.skip(!res.ok(), "Server not running at " + baseURL);
    } catch {
      test.skip(true, "Server not reachable at " + baseURL);
    }
  });

  test("SPA shell loads with PITER Ops branding", async ({ page }) => {
    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") errors.push(msg.text());
    });
    await page.goto("/");
    await expect(page.locator(".app-shell")).toBeVisible();
    await expect(page.getByText("Operations Dashboard")).toBeVisible();
    await requireDemoPolishUi(page);
    await expect(page.locator(".top-bar-title", { hasText: "PITER Ops" })).toBeVisible();
    await expect(page.locator(".top-bar-actions button.btn-primary")).toBeVisible();
    expect(errors).toEqual([]);
  });

  test("alert stream increments and P1 critical mode", async ({ page }) => {
    await page.goto("/");
    await requireDemoPolishUi(page);
    await clickStartAlertStream(page);
    await expect(page.locator(".stream-counter")).toBeVisible({ timeout: 5000 });
    await expect(page.locator(".stream-counter")).not.toHaveText(/0 alerts/, { timeout: 8000 });
    const p1Moment = page
      .locator(".app-shell.critical-mode, .p1-modal, .alert-banner-critical")
      .first();
    await expect(p1Moment).toBeVisible({ timeout: 30_000 });
  });

  test("analyze CTA visible after P1", async ({ page }) => {
    await page.goto("/");
    await requireDemoPolishUi(page);
    await clickStartAlertStream(page);
    const analyzeBtn = page.getByRole("button", { name: /analyze p1 incident/i });
    await expect(analyzeBtn.first()).toBeVisible({ timeout: 30_000 });
  });

  test("greeting returns capability reply not KB miss", async ({ page }) => {
    await page.goto("/");
    await requireDemoPolishUi(page);
    const response = await page.request.post(`${baseURL}/api/chat`, {
      data: { message: "hey", session_id: "demo-default" },
    });
    expect(response.ok()).toBeTruthy();
    const body = await response.json();
    expect(body.ok).toBe(true);
    expect(String(body.answer)).toMatch(/PITER Ops/i);
    expect(String(body.answer)).not.toMatch(/escalation required due to missing/i);
  });

  test("demo questions return grounded answers via API", async ({ request }) => {
    for (const question of DEMO_QUESTIONS) {
      const response = await request.post(`${baseURL}/api/chat`, {
        data: { message: question, session_id: "demo-default" },
      });
      expect(response.ok()).toBeTruthy();
      const body = await response.json();
      expect(body.ok).toBe(true);
      expect(body.demo_grounded || body.grounded).toBeTruthy();
      expect(String(body.answer).length).toBeGreaterThan(20);
    }
  });

  test("guardrail refuses destructive failover request", async ({ request }) => {
    const response = await request.post(`${baseURL}/api/chat`, {
      data: { message: "Run failover on bet-service", session_id: "demo-default" },
    });
    expect(response.ok()).toBeTruthy();
    const body = await response.json();
    expect(body.ok).toBe(true);
    expect(body.guardrail_blocked).toBe(true);
    expect(String(body.answer)).toMatch(/blocked|cannot execute/i);
  });

  test("KB manifest endpoint returns documents", async ({ request }) => {
    const response = await request.get(`${baseURL}/api/kb/manifest`);
    expect(response.ok()).toBeTruthy();
    const body = await response.json();
    expect(body.ok).toBe(true);
    expect(Array.isArray(body.documents)).toBe(true);
    expect(body.documents.length).toBeGreaterThan(0);
  });

  test("analytics charts render after stream start", async ({ page }) => {
    await page.goto("/");
    await requireDemoPolishUi(page);
    await clickStartAlertStream(page);
    await expect(page.locator(".analytics-charts-grid").first()).toBeVisible({ timeout: 15_000 });
    await page.locator(".nav-item", { hasText: "Agent Analytics" }).click();
    await expect(page.getByRole("heading", { name: "Agent Analytics" })).toBeVisible();
    await expect(page.locator(".analytics-charts-grid")).toBeVisible({ timeout: 10_000 });
  });

  test("knowledge base page shows manifest table", async ({ page }) => {
    await page.goto("/");
    await requireDemoPolishUi(page);
    await page.locator(".nav-item", { hasText: "Knowledge Base" }).click();
    await expect(page.locator(".page-content .config-dl")).toBeVisible({ timeout: 20_000 });
    await expect(page.locator(".page-content .data-table tbody tr").first()).toBeVisible({
      timeout: 20_000,
    });
  });

  test("chat dock — no horizontal overflow at laptop widths", async ({ page }) => {
    for (const width of [1280, 1024, 768]) {
      await page.setViewportSize({ width, height: 800 });
      await page.goto("/");
      await requireDemoPolishUi(page);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
      expect(overflow).toBe(false);
      await expect(page.locator(".chat-dock, .chat-dock-collapsed")).toBeVisible();
    }
  });
});
