import { test, expect } from "@playwright/test";

test.describe("Auth flow", () => {
  test("redirects to /auth when no API key", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/auth/);
  });

  test("shows demo key button on auth page", async ({ page }) => {
    await page.goto("/auth");
    await expect(page.getByText("Use Demo Key")).toBeVisible();
  });

  test("can fetch and use demo key", async ({ page }) => {
    await page.goto("/auth");
    await page.getByText("Use Demo Key").click();
    await expect(page).toHaveURL("/", { timeout: 10000 });
  });
});

test.describe("Demo flow", () => {
  test("can list and launch demo vehicles", async ({ page }) => {
    await page.goto("/auth");
    await page.getByText("Use Demo Key").click();
    await page.waitForURL("/");

    await page.getByText("Show Demo Vehicles").click();
    await expect(page.getByText("Bajaj RE 2019")).toBeVisible({ timeout: 10000 });

    await page.getByText("Bajaj RE 2019").click();
    await expect(page.getByText("Assessment Progress")).toBeVisible({ timeout: 15000 });
  });
});
