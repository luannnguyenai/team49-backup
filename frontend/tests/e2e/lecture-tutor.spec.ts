import { expect, test, type Page } from "@playwright/test";

async function signInAsOnboardedLearner(page: Page, label: string) {
  const accessToken = `e2e-access-${label}-${Date.now()}`;
  const refreshToken = `e2e-refresh-${label}-${Date.now()}`;
  const expiresAt = String(Date.now() + 30 * 60 * 1000);
  const cookiePairs = [
    {
      name: "al_access_token",
      value: accessToken,
    },
    {
      name: "al_refresh_token",
      value: refreshToken,
    },
    {
      name: "al_token_expires_at",
      value: expiresAt,
    },
  ] as const;

  await page.context().addCookies(
    cookiePairs.flatMap((cookie) => [
      {
        ...cookie,
        url: "http://127.0.0.1:3000",
      },
      {
        ...cookie,
        url: "http://localhost:3000",
      },
    ]),
  );

  await page.goto("/");
  await page.evaluate(
    ({ accessToken: access, refreshToken: refresh, expiresAt: expires }) => {
      document.cookie = `al_access_token=${access}; Path=/; SameSite=Lax`;
      document.cookie = `al_refresh_token=${refresh}; Path=/; SameSite=Lax`;
      document.cookie = `al_token_expires_at=${expires}; Path=/; SameSite=Lax`;
    },
    { accessToken, refreshToken, expiresAt },
  );
}

/**
 * US3 E2E: Lecture and tutor journey.
 *
 * These tests validate that:
 * 1. Course overview leads into the learning unit page
 * 2. The learning unit page shows the lecture shell with AI Tutor
 * 3. Legacy /tutor redirects into the course-first experience
 * 4. Legacy /learn redirects to the public catalog
 */

test.describe("US3: unified lecture experience", () => {
  test("legacy tutor page redirects to the default course overview", async ({ page }) => {
    await page.goto("/tutor");
    await page.waitForURL(/\/courses\/cs231n$/, { timeout: 5000 });
  });

  test("legacy learn page redirects to course catalog", async ({ page }) => {
    await page.goto("/learn");

    await page.waitForURL(/\/$/, { timeout: 5000 });
  });
});

test.describe("US3: learning unit page", () => {
  test("CS231n lecture 1 learning unit page loads with course breadcrumb", async ({
    page,
  }) => {
    await signInAsOnboardedLearner(page, "learning-shell");
    await page.goto("/courses/cs231n/learn/lecture-1-introduction");

    await expect(page.getByText("Lecture 1: Introduction")).toBeVisible();
    await expect(
      page.getByText("CS231n: Deep Learning for Computer Vision"),
    ).toBeVisible();
  });

  test("AI Tutor toggle is visible on learning unit page", async ({
    page,
  }) => {
    await signInAsOnboardedLearner(page, "tutor-toggle");
    await page.goto("/courses/cs231n/learn/lecture-1-introduction");

    await expect(page.getByText("AI Tutor")).toBeVisible();
  });

  test(
    "clicking AI Tutor opens the in-context tutor panel",
    async ({ page }) => {
      await signInAsOnboardedLearner(page, "tutor-panel");
      await page.goto("/courses/cs231n/learn/lecture-1-introduction");

      await page.getByText("AI Tutor").click();

      await expect(
        page.getByPlaceholder("Ask about this lecture..."),
      ).toBeVisible();
    },
  );
});
