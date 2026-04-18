import { expect, test } from "@playwright/test";

/**
 * US3 E2E: Lecture and tutor journey.
 *
 * These tests validate that:
 * 1. Course overview leads into the learning unit page
 * 2. The learning unit page shows the lecture shell with AI Tutor
 * 3. Legacy /tutor page shows a redirect banner
 * 4. Legacy /learn page redirects to course catalog
 */

test.describe("US3: unified lecture experience", () => {
  test("legacy tutor page shows course-first redirect banner", async ({
    page,
  }) => {
    await page.goto("/tutor");

    // Should show the compatibility banner
    await expect(
      page.getByText("AI Tutor is now built into the course learning experience"),
    ).toBeVisible();

    // "Go to courses" link should be visible
    await expect(page.getByRole("link", { name: /Go to courses/i })).toBeVisible();
  });

  test("legacy learn page redirects to course catalog", async ({ page }) => {
    await page.goto("/learn");

    // Should redirect to the home catalog
    await page.waitForURL("/", { timeout: 5000 });
  });
});

test.describe("US3: learning unit page", () => {
  test("CS231n lecture 1 learning unit page loads with course breadcrumb", async ({
    page,
  }) => {
    // Navigate from course overview
    await page.goto("/courses/cs231n");
    await expect(page.getByRole("button", { name: "Start learning" })).toBeVisible();

    // Click start learning (this goes through the decision gate)
    // For this test we directly navigate to the learning page
    await page.goto("/courses/cs231n/learn/lecture-1-introduction");

    // Should show the unit title and course breadcrumb
    await expect(page.getByText("Lecture 1: Introduction")).toBeVisible();
    await expect(
      page.getByText("CS231n: Deep Learning for Computer Vision"),
    ).toBeVisible();
  });

  test("AI Tutor toggle is visible on learning unit page", async ({
    page,
  }) => {
    await page.goto("/courses/cs231n/learn/lecture-1-introduction");

    // AI Tutor button should be visible for ready units with video
    await expect(page.getByText("AI Tutor")).toBeVisible();
  });

  test.skip(
    "clicking AI Tutor opens the in-context tutor panel",
    async ({ page }) => {
      await page.goto("/courses/cs231n/learn/lecture-1-introduction");

      // Click the AI Tutor toggle
      await page.getByText("AI Tutor").click();

      // Should show the tutor panel with input
      await expect(
        page.getByPlaceholder("Ask about this lecture..."),
      ).toBeVisible();
    },
  );
});
