import { test, expect, type Page } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const baseURL = process.env.PITER_BASE_URL || "http://127.0.0.1:8080";
const UI_VERSION = "demo-polish-v6";
const screenshotDir = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../screenshots/final",
);

async function requireDemoPolishUi(page: Page): Promise<void> {
  const marker = page.locator(`.app-shell[data-ui-version="${UI_VERSION}"]`);
  const hasMarker = await marker.isVisible().catch(() => false);
  test.skip(
    !hasMarker,
    `Built ${UI_VERSION} SPA not served — rebuild frontend and redeploy before running against ${baseURL}`,
  );
}

function collectConsoleErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(msg.text());
  });
  return errors;
}

test.describe("Full application sweep", () => {
  test.beforeEach(async ({ request }) => {
    try {
      const res = await request.get(`${baseURL}/api/health`);
      test.skip(!res.ok(), "Server not running at " + baseURL);
    } catch {
      test.skip(true, "Server not reachable at " + baseURL);
    }
  });

  test("shell — footer, fonts, navigation, no console errors", async ({ page }) => {
    const errors = collectConsoleErrors(page);
    await page.goto("/");
    await requireDemoPolishUi(page);

    await expect(page.locator(".app-footer")).toBeVisible();
    await expect(page.locator(".app-footer-badge", { hasText: UI_VERSION })).toBeVisible();

    const fontFamily = await page.locator(".app-shell").evaluate((el) =>
      getComputedStyle(el).getPropertyValue("font-family"),
    );
    expect(fontFamily.toLowerCase()).toContain("ibm plex sans");

    const pages = [
      "Agent Analytics",
      "Incident History",
      "Analyzer",
      "Knowledge Base",
      "AWS / Bedrock",
      "Demo Guide",
    ];
    for (const label of pages) {
      await page.locator(".nav-item", { hasText: label }).click();
      await expect(page.locator(".page-content")).toBeVisible();
    }

    await page.locator(".nav-item", { hasText: "Live Demo" }).click();
    expect(errors).toEqual([]);
  });

  test("demo controls — storm, pause, reset", async ({ page }) => {
    const errors = collectConsoleErrors(page);
    await page.goto("/");
    await requireDemoPolishUi(page);

    await page.getByRole("button", { name: /start.*alert stream/i }).click();
    await expect(page.locator(".stream-counter, .stream-live-pulse").first()).toBeVisible({
      timeout: 15_000,
    });

    await page.getByRole("button", { name: /pause/i }).click();
    await page.getByRole("button", { name: /reset/i }).click();
    expect(errors).toEqual([]);
  });

  test("demo — analysis waiting animation", async ({ page }) => {
    await page.goto("/");
    await requireDemoPolishUi(page);
    await page.getByRole("button", { name: /start.*alert stream/i }).click();
    await expect(page.locator(".p1-modal, .alert-banner-critical").first()).toBeVisible({
      timeout: 45_000,
    });
    const analyzeBtn = page.getByRole("button", { name: /analyze.*incident/i }).first();
    if (await analyzeBtn.isVisible()) {
      await analyzeBtn.click();
      await expect(page.locator(".analysis-in-progress-card, .enrichment-pipeline").first()).toBeVisible({
        timeout: 10_000,
      });
    }
  });

  test("analyzer — structured panel v6 layout", async ({ page }) => {
    const errors = collectConsoleErrors(page);
    await page.goto("/");
    await requireDemoPolishUi(page);
    await page.locator(".nav-item", { hasText: "Analyzer" }).click();

    await page.locator("#svc").fill("wallet-service");
    await page.locator("#env").fill("GIB-UKGC");
    await page.locator("#symptom").fill("Replication lag exceeded threshold after wallet-service deploy");
    await page.getByRole("button", { name: /run analysis/i }).click();

    const panel = page.locator("#piter-analysis-panel");
    await expect(panel).toBeVisible({ timeout: 120_000 });
    await expect(panel.getByText("Agent Enrichment Pipeline")).toBeVisible();
    await expect(panel.getByRole("heading", { name: "Business impact" })).toBeVisible();
    await expect(panel.getByText("Recommended action plan")).toBeVisible();
    await expect(panel.getByText("Correlation chain")).toBeVisible();

    const panelText = await panel.innerText();
    expect(panelText).not.toMatch(/\*\*[^*]+\*\*/);
    expect(panelText).not.toContain("Source: Bedrock Agent");

    await panel.screenshot({
      path: path.join(screenshotDir, "16_structured_analysis_panel.png"),
      fullPage: true,
    });
    expect(errors).toEqual([]);
  });

  test("chat dock — send and receive", async ({ page }) => {
    const errors = collectConsoleErrors(page);
    await page.goto("/");
    await requireDemoPolishUi(page);

    const chatToggle = page.locator(".chat-dock-toggle, .chat-rail-toggle").first();
    if (await chatToggle.isVisible()) {
      await chatToggle.click();
    }

    const textarea = page.locator(".chat-compose textarea, textarea[placeholder*='message' i]").first();
    await expect(textarea).toBeVisible({ timeout: 10_000 });
    await textarea.fill("What is the current system status?");
    await page.getByRole("button", { name: /send/i }).click();
    await expect(page.locator(".chat-bubble").last()).toBeVisible({ timeout: 60_000 });
    expect(errors).toEqual([]);
  });

  test("footer links navigate", async ({ page }) => {
    await page.goto("/");
    await requireDemoPolishUi(page);

    await page.getByRole("button", { name: "Bedrock Status" }).click();
    await expect(page.locator(".page-content")).toBeVisible({ timeout: 10_000 });

    await page.getByRole("button", { name: "KB Manifest" }).click();
    await expect(page.locator(".page-content")).toBeVisible({ timeout: 10_000 });
  });
});
