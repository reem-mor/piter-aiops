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
  await expect(marker).toBeVisible({ timeout: 15_000 });
}

/** Clear stale Agent Copilot history so screenshots show a clean rail. */
async function clearChatRail(page: Page): Promise<void> {
  const clearBtn = page.getByRole("button", { name: /clear chat/i });
  if (await clearBtn.isVisible().catch(() => false)) {
    await clearBtn.click();
    await page.waitForTimeout(500);
  }
}

/** Mask real recipient emails/phones in the escalation modal before capture (PII hygiene). */
async function maskEscalationRecipients(page: Page): Promise<void> {
  await page.evaluate(() => {
    const mask = (text: string) =>
      text.replace(
        /([A-Za-z0-9._%+-])[A-Za-z0-9._%+-]*@([A-Za-z0-9.-]+)/g,
        (_m, first: string, domain: string) => `${first}***@${domain.replace(/^[^.]+/, "***")}`,
      );
    document.querySelectorAll(".escalation-recipient-list li").forEach((el) => {
      if (el.textContent && /@/.test(el.textContent)) {
        el.textContent = mask(el.textContent.trim());
      }
    });
  });
}

test.describe("Submission screenshot capture", () => {
  test.use({ viewport: { width: 1920, height: 1080 } });
  test.setTimeout(180_000);

  test.beforeEach(async ({ request }) => {
    const res = await request.get(`${baseURL}/api/health`);
    test.skip(!res.ok(), "Server not running at " + baseURL);
  });

  test("01 — main NOC dashboard", async ({ page }) => {
    await page.goto("/");
    await requireDemoPolishUi(page);
    await clearChatRail(page);
    await expect(page.getByText("Operations Dashboard")).toBeVisible();
    await page.waitForTimeout(1500);
    await page.screenshot({
      path: path.join(screenshotDir, "01_dashboard.png"),
      fullPage: true,
    });
  });

  test("05/16 — analyze alert with structured output", async ({ page }) => {
    await page.goto("/");
    await requireDemoPolishUi(page);
    await clearChatRail(page);
    await page.locator(".nav-item", { hasText: "Analyzer" }).click();
    await expect(page.getByRole("heading", { name: "Incident Analyzer" })).toBeVisible();

    await page.locator("#svc").fill("wallet-service");
    await page.locator("#env").fill("GIB-UKGC");
    await page
      .locator("#symptom")
      .fill(
        "Replication lag exceeded threshold after wallet-service v4.12.3 deploy — correlate to INC-2025-11-04",
      );
    await page.getByRole("button", { name: /run analysis/i }).click();

    const panel = page.locator("#piter-analysis-panel");
    await expect(panel).toBeVisible({ timeout: 120_000 });
    await expect(panel.getByText("Correlation chain")).toBeVisible({ timeout: 30_000 });

    await page.screenshot({
      path: path.join(screenshotDir, "05_investigation_detail_triage.png"),
      fullPage: true,
    });
    await panel.screenshot({
      path: path.join(screenshotDir, "16_structured_analysis_panel.png"),
    });
  });

  test("06 — KB-grounded citations in analysis", async ({ page }) => {
    await page.goto("/");
    await requireDemoPolishUi(page);
    await clearChatRail(page);
    await page.locator(".nav-item", { hasText: "Analyzer" }).click();

    await page.locator("#svc").fill("auth-service");
    await page.locator("#env").fill("MGM");
    await page
      .locator("#symptom")
      .fill("Many users cannot log in after the latest production deployment");
    await page.getByRole("button", { name: /run analysis/i }).click();

    const panel = page.locator("#piter-analysis-panel");
    await expect(panel).toBeVisible({ timeout: 120_000 });
    await expect(panel.getByRole("heading", { name: "Sources" })).toBeVisible({ timeout: 30_000 });
    await expect(panel.locator(".piter-chip-list .piter-chip").first()).toBeVisible({ timeout: 30_000 });

    await page.screenshot({
      path: path.join(screenshotDir, "06_rag_citations.png"),
      fullPage: true,
    });
  });

  test("08 — chat memory follow-up", async ({ page }) => {
    const sessionId = `screenshot-memory-${Date.now()}`;
    await page.goto("/");
    await requireDemoPolishUi(page);

    const chatToggle = page.locator(".chat-dock-toggle, .chat-rail-toggle").first();
    if (await chatToggle.isVisible()) {
      await chatToggle.click();
    }

    // Fresh session so the rail only shows this demo's question + follow-up.
    const newSessionBtn = page.getByRole("button", { name: /new session/i });
    if (await newSessionBtn.isVisible().catch(() => false)) {
      await newSessionBtn.click();
      await page.waitForTimeout(500);
    }

    const textarea = page.locator(".chat-compose textarea, textarea[placeholder*='message' i]").first();
    await expect(textarea).toBeVisible({ timeout: 10_000 });

    await textarea.fill(
      "Many users cannot log in after the latest production deployment on auth-service in MGM. Severity critical.",
    );
    await page.getByRole("button", { name: /send/i }).click();
    const assistantBubble = page.locator(".chat-bubble.chat-assistant:not(.chat-thinking)");
    await expect(assistantBubble.last()).toBeVisible({ timeout: 120_000 });

    await textarea.fill("What should I check next?");
    await page.getByRole("button", { name: /send/i }).click();
    await expect(assistantBubble).toHaveCount(2, { timeout: 120_000 });
    const followUp = assistantBubble.last();
    const followUpText = await followUp.innerText();
    expect(followUpText.length).toBeGreaterThan(20);
    await page.waitForTimeout(2000);

    await page.screenshot({
      path: path.join(screenshotDir, "08_memory_followup_context.png"),
      fullPage: true,
    });

    void sessionId;
  });

  test("09 — escalation preview modal", async ({ page }) => {
    await page.goto("/");
    await requireDemoPolishUi(page);
    await clearChatRail(page);
    await page.locator(".nav-item", { hasText: "Analyzer" }).click();

    await page.locator("#svc").fill("wallet-service");
    await page.locator("#env").fill("GIB-UKGC");
    await page.locator("#symptom").fill("Replication lag exceeded threshold after deploy");
    await page.getByRole("button", { name: /run analysis/i }).click();

    const panel = page.locator("#piter-analysis-panel");
    await expect(panel).toBeVisible({ timeout: 120_000 });
    await page.getByRole("button", { name: /escalate on-call/i }).click();

    const modal = page.locator(".modal-backdrop");
    await expect(modal).toBeVisible();
    await expect(page.getByText(/confirm dispatch|escalation preview|message preview/i).first()).toBeVisible();

    await maskEscalationRecipients(page);
    await page.waitForTimeout(500);
    await page.screenshot({
      path: path.join(screenshotDir, "09_escalation_preview.png"),
      fullPage: false,
    });
  });

  test("02 — incident history table", async ({ page }) => {
    await page.goto("/");
    await requireDemoPolishUi(page);
    await clearChatRail(page);
    await page.locator(".nav-item", { hasText: "Incident History" }).click();
    await expect(page.getByText("History & Investigations")).toBeVisible({ timeout: 15_000 });
    await page.waitForTimeout(1500);
    await page.screenshot({
      path: path.join(screenshotDir, "02_investigations_table.png"),
      fullPage: true,
    });
  });

  test("03/04 — alert storm running and P1 detected", async ({ page }) => {
    await page.goto("/");
    await requireDemoPolishUi(page);
    await clearChatRail(page);
    await page.getByRole("button", { name: /start alert stream/i }).click();

    // Mid-storm: alerts flowing, before the P1 popup (fires ~20s wall clock).
    await page.waitForTimeout(12_000);
    await page.screenshot({
      path: path.join(screenshotDir, "03_alert_storm_running.png"),
      fullPage: true,
    });

    // P1 candidate detected.
    await expect(page.getByText(/P1 candidate detected|P1 incident candidate/i).first()).toBeVisible({
      timeout: 60_000,
    });
    await page.waitForTimeout(1000);
    await page.screenshot({
      path: path.join(screenshotDir, "04_p1_detected.png"),
      fullPage: true,
    });
  });

  test("10 — post-mortems page", async ({ page }) => {
    await page.goto("/");
    await requireDemoPolishUi(page);
    await clearChatRail(page);
    await page.locator(".nav-item", { hasText: "Post-Mortems" }).click();
    await expect(page.getByText(/post-mortem/i).first()).toBeVisible({ timeout: 15_000 });
    await page.waitForTimeout(1500);
    await page.screenshot({
      path: path.join(screenshotDir, "10_post_mortem_summary.png"),
      fullPage: true,
    });
  });

  test("11 — knowledge base page with upload panel", async ({ page }) => {
    await page.goto("/");
    await requireDemoPolishUi(page);
    await clearChatRail(page);
    await page.locator(".nav-item", { hasText: "Knowledge Base" }).click();
    await expect(page.getByText("Documents indexed for RAG", { exact: false })).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByRole("heading", { name: "Upload runbook" })).toBeVisible({
      timeout: 15_000,
    });
    await page.waitForTimeout(1500);
    await page.screenshot({
      path: path.join(screenshotDir, "11_knowledge_base.png"),
      fullPage: true,
    });
  });

  test("13b — AWS / Bedrock status with action groups", async ({ page }) => {
    await page.goto("/");
    await requireDemoPolishUi(page);
    await clearChatRail(page);
    await page.locator(".nav-item", { hasText: "AWS / Bedrock" }).click();
    await expect(page.getByText("AWS / Bedrock Status").first()).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("Action groups").first()).toBeVisible({ timeout: 30_000 });
    await page.waitForTimeout(2000);
    await page.screenshot({
      path: path.join(screenshotDir, "13b_settings_aws_status.png"),
      fullPage: true,
    });
  });

  test("demo-correlation-chain — wallet deploy lag similar incident", async ({ page }) => {
    await page.goto("/");
    await requireDemoPolishUi(page);
    await clearChatRail(page);
    await page.locator(".nav-item", { hasText: "Analyzer" }).click();

    await page.locator("#svc").fill("wallet-service");
    await page.locator("#env").fill("GIB-UKGC");
    await page
      .locator("#symptom")
      .fill(
        "Replication lag alert after wallet-service v4.12.3 deployment — find similar incident INC-2025-11-04",
      );
    await page.getByRole("button", { name: /run analysis/i }).click();

    const panel = page.locator("#piter-analysis-panel");
    await expect(panel).toBeVisible({ timeout: 120_000 });
    await expect(panel.getByText("Correlation chain")).toBeVisible({ timeout: 30_000 });

    const panelText = await panel.innerText();
    const hasDeploy = /v4\.12\.3|deploy/i.test(panelText);
    const hasLag = /replication|lag/i.test(panelText);
    expect(hasDeploy || hasLag).toBeTruthy();

    await panel.screenshot({
      path: path.join(screenshotDir, "demo-wallet-v4-12-3-correlation-chain.png"),
    });
  });
});
