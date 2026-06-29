import { test, expect, type Page } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const baseURL = process.env.PITER_BASE_URL || "http://127.0.0.1:8080";
const UI_VERSION = "demo-polish-v6";
// Evidence shots only — keep out of screenshots/final (modal can show unmasked recipient emails).
const screenshotDir = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../test-results/evidence",
);

async function requireDemoPolishUi(page: Page): Promise<void> {
  const marker = page.locator(`.app-shell[data-ui-version="${UI_VERSION}"]`);
  const hasMarker = await marker.isVisible().catch(() => false);
  test.skip(
    !hasMarker,
    `Built ${UI_VERSION} SPA not served — rebuild frontend and redeploy before running against ${baseURL}`,
  );
}

test.describe("Output hardening evidence", () => {
  test.beforeEach(async ({ request }) => {
    try {
      const res = await request.get(`${baseURL}/api/health`);
      test.skip(!res.ok(), "Server not running at " + baseURL);
    } catch {
      test.skip(true, "Server not reachable at " + baseURL);
    }
  });

  test("structured analysis panel — no raw markdown", async ({ page }) => {
    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") errors.push(msg.text());
    });

    await page.goto("/");
    await requireDemoPolishUi(page);
    await page.locator(".nav-item", { hasText: "Analyzer" }).click();
    await expect(page.getByRole("heading", { name: "Incident Analyzer" })).toBeVisible();

    await page.locator("#svc").fill("wallet-service");
    await page.locator("#env").fill("GIB-UKGC");
    await page.locator("#symptom").fill("Replication lag exceeded threshold after wallet-service deploy");
    await page.getByRole("button", { name: /run analysis/i }).click();

    const panel = page.locator("#piter-analysis-panel");
    await expect(panel).toBeVisible({ timeout: 120_000 });
    await expect(panel.getByText("Recommended action plan")).toBeVisible({ timeout: 30_000 });
    await expect(panel.getByRole("heading", { name: "Business impact" })).toBeVisible();
    await expect(panel.locator(".correlation-chain-item").first()).toBeVisible();

    const panelText = await panel.innerText();
    expect(panelText).not.toMatch(/\*\*[^*]+\*\*/);

    await panel.screenshot({
      path: path.join(screenshotDir, "16_structured_analysis_panel.png"),
      fullPage: true,
    });
    expect(errors).toEqual([]);
  });

  test("tokenless escalation modal — preview only, no token field", async ({ page }) => {
    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") errors.push(msg.text());
    });

    await page.goto("/");
    await requireDemoPolishUi(page);
    await page.locator(".nav-item", { hasText: "Analyzer" }).click();

    await page.locator("#svc").fill("wallet-service");
    await page.locator("#env").fill("GIB-UKGC");
    await page.locator("#symptom").fill("Replication lag exceeded threshold");
    await page.getByRole("button", { name: /run analysis/i }).click();

    const panel = page.locator("#piter-analysis-panel");
    await expect(panel).toBeVisible({ timeout: 120_000 });
    await page.getByRole("button", { name: /escalate on-call/i }).click();

    const modal = page.locator(".modal-backdrop");
    await expect(modal).toBeVisible();
    await expect(page.locator('input[type="password"]')).toHaveCount(0);
    await expect(page.getByPlaceholder(/token/i)).toHaveCount(0);
    await expect(page.getByText(/confirm dispatch/i)).toBeVisible();

    await modal.screenshot({
      path: path.join(screenshotDir, "17_tokenless_escalation_modal.png"),
    });
    expect(errors).toEqual([]);
  });
});
