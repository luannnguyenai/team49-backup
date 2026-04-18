import { expect, test } from "@playwright/test";

/**
 * US2 E2E: Auth-to-skill-test course-entry flow.
 *
 * These tests validate that:
 * 1. Unauthenticated visitors clicking "Start learning" get redirected to login
 * 2. Course context is preserved through the auth redirect
 * 3. Authenticated users without skill-test see the assessment gate
 * 4. Authenticated users with recommendations see tab UI
 *
 * Note: These tests require a running backend with auth and assessment services.
 * They are designed as Playwright journey specs and may need test user seeding.
 */

test.describe("US2: course gating flow", () => {
  test("unauthenticated start-learning redirects to login with course context", async ({
    page,
  }) => {
    // Visit CS231n overview
    await page.goto("/courses/cs231n");

    // Wait for overview to load
    await expect(page.getByRole("button", { name: "Start learning" })).toBeVisible();

    // Click start learning
    await page.getByRole("button", { name: "Start learning" }).click();

    // Should redirect to login with course context preserved
    await page.waitForURL(/\/login/);
    const url = new URL(page.url());
    const nextParam = url.searchParams.get("next") ?? url.searchParams.get("from");
    expect(nextParam).toContain("/courses/cs231n/start");
  });

  test("coming-soon course blocks start action regardless of auth state", async ({ page }) => {
    // Visit CS224n overview (coming soon)
    await page.goto("/courses/cs224n");

    // The start button should be disabled with "Coming soon" text
    const startButton = page.getByRole("button", { name: "Coming soon" });
    await expect(startButton).toBeVisible();
    await expect(startButton).toBeDisabled();
  });

  test("public catalog shows both courses without tab UI when not authenticated", async ({
    page,
  }) => {
    await page.goto("/");

    // Both courses visible
    await expect(page.getByText("CS231n: Deep Learning for Computer Vision")).toBeVisible();
    await expect(
      page.getByText("CS224n: Natural Language Processing with Deep Learning"),
    ).toBeVisible();

    // No tab UI for unauthenticated visitors
    await expect(page.getByRole("tablist")).not.toBeVisible();
  });
});

test.describe("US2: personalized catalog after skill test", () => {
  // These tests require authenticated + skill-test-completed user state.
  // They serve as journey specs — run with seeded test data.

  test.skip(
    "authenticated user with completed skill test sees recommended and all-courses tabs",
    async ({ page }) => {
      // This test requires a pre-seeded authenticated session with
      // completed assessment and generated recommendations.
      // Skip until e2e test infrastructure supports user seeding.

      await page.goto("/");

      // Tab bar should be visible
      await expect(page.getByRole("tablist")).toBeVisible();
      await expect(page.getByRole("tab", { name: "Recommended for you" })).toBeVisible();
      await expect(page.getByRole("tab", { name: "All courses" })).toBeVisible();
    },
  );

  test.skip(
    "authenticated user without recommendations sees all-courses without tabs",
    async ({ page }) => {
      // This test requires a pre-seeded authenticated session WITHOUT
      // completed assessment.

      await page.goto("/");

      // No tab bar — just the all-courses view
      await expect(page.getByRole("tablist")).not.toBeVisible();
      await expect(page.getByText("CS231n: Deep Learning for Computer Vision")).toBeVisible();
    },
  );
});
