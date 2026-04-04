import { test, expect } from "@playwright/test";

test.describe("OpenRaven Web UI", () => {
  test("health endpoint returns ok", async ({ request }) => {
    const res = await request.get("/health");
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.status).toBe("ok");
  });

  test("status API returns knowledge base stats", async ({ request }) => {
    const res = await request.get("/api/status");
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body).toHaveProperty("total_files");
    expect(body).toHaveProperty("total_entities");
    expect(body).toHaveProperty("topic_count");
  });

  test("discovery API returns array", async ({ request }) => {
    const res = await request.get("/api/discovery");
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(Array.isArray(body)).toBeTruthy();
  });

  test("ask API validates required fields", async ({ request }) => {
    const res = await request.post("/api/ask", {
      data: {},
      headers: { "Content-Type": "application/json" },
    });
    // Should return 400 for missing question
    expect(res.status()).toBe(400);
  });

  test("homepage loads with Ask page", async ({ page }) => {
    await page.goto("/");
    // Nav should be visible
    await expect(page.locator("nav")).toBeVisible();
    await expect(page.locator("nav")).toContainText("OpenRaven");
    // Ask input should be present
    await expect(
      page.getByPlaceholder("Ask your knowledge base...")
    ).toBeVisible();
    // Ask button should be present
    await expect(page.getByRole("button", { name: "Ask" })).toBeVisible();
  });

  test("navigation links work", async ({ page }) => {
    await page.goto("/");

    // Click "Add Files" nav link
    await page.getByRole("link", { name: "Add Files" }).click();
    await expect(page).toHaveURL(/\/ingest/);
    await expect(page.getByText("Add Documents")).toBeVisible();

    // Click "Status" nav link
    await page.getByRole("link", { name: "Status" }).click();
    await expect(page).toHaveURL(/\/status/);
    await expect(page.getByText("Knowledge Base Status")).toBeVisible();

    // Click back to "Ask"
    await page.getByRole("link", { name: "Ask" }).click();
    await expect(page).toHaveURL("/");
  });

  test("status page shows stat cards", async ({ page }) => {
    await page.goto("/status");
    await expect(page.getByText("Knowledge Base Status")).toBeVisible();
    // Should show the 4 stat cards (use exact match to avoid nav link conflicts)
    await expect(page.getByText("Files", { exact: true })).toBeVisible();
    await expect(page.getByText("Concepts", { exact: true })).toBeVisible();
    await expect(page.getByText("Connections", { exact: true })).toBeVisible();
    await expect(page.getByText("Topics", { exact: true })).toBeVisible();
  });

  test("ingest page has file uploader", async ({ page }) => {
    await page.goto("/ingest");
    await expect(page.getByText("Add Documents")).toBeVisible();
    await expect(page.getByText("Drop files here")).toBeVisible();
    await expect(page.getByText("Browse files")).toBeVisible();
  });

  test("ask page sends question and shows user message", async ({ page }) => {
    await page.goto("/");
    const input = page.getByPlaceholder("Ask your knowledge base...");
    await input.fill("What is OpenRaven?");
    await page.getByRole("button", { name: "Ask" }).click();

    // User message should appear immediately
    await expect(page.getByText("What is OpenRaven?")).toBeVisible();

    // "Thinking..." indicator should appear while waiting for response
    await expect(page.getByText("Thinking...")).toBeVisible({ timeout: 3000 });
  });
});
