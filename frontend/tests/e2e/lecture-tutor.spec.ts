import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

async function signInAsOnboardedLearner(
  page: Page,
  request: APIRequestContext,
  label: string,
) {
  const email = `e2e-${label}-${Date.now()}@example.com`;
  const password = "Password123";
  const fullName = `E2E ${label}`;

  const register = await request.post("http://127.0.0.1:8000/api/auth/register", {
    data: {
      email,
      password,
      full_name: fullName,
    },
  });
  expect(register.ok()).toBeTruthy();

  const tokens = (await register.json()) as {
    access_token: string;
    refresh_token: string;
    expires_in: number;
  };

  const onboard = await request.put("http://127.0.0.1:8000/api/users/me/onboarding", {
    headers: {
      Authorization: `Bearer ${tokens.access_token}`,
    },
    data: {
      known_topic_ids: [],
      desired_module_ids: [],
      available_hours_per_week: 6,
      target_deadline: "2026-12-31",
      preferred_method: "video",
    },
  });
  expect(onboard.ok()).toBeTruthy();

  const expiresAt = String(Date.now() + tokens.expires_in * 1000);
  const cookiePairs = [
    {
      name: "al_access_token",
      value: tokens.access_token,
    },
    {
      name: "al_refresh_token",
      value: tokens.refresh_token,
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
    request,
  }) => {
    await signInAsOnboardedLearner(page, request, "learning-shell");
    await page.goto("/courses/cs231n/learn/lecture-1-introduction");

    await expect(page.getByText("Lecture 1: Introduction")).toBeVisible();
    await expect(
      page.getByText("CS231n: Deep Learning for Computer Vision"),
    ).toBeVisible();
  });

  test("AI Tutor toggle is visible on learning unit page", async ({
    page,
    request,
  }) => {
    await signInAsOnboardedLearner(page, request, "tutor-toggle");
    await page.goto("/courses/cs231n/learn/lecture-1-introduction");

    await expect(page.getByText("AI Tutor")).toBeVisible();
  });

  test(
    "clicking AI Tutor opens the in-context tutor panel",
    async ({ page, request }) => {
      await signInAsOnboardedLearner(page, request, "tutor-panel");
      await page.goto("/courses/cs231n/learn/lecture-1-introduction");

      await page.getByText("AI Tutor").click();

      await expect(
        page.getByPlaceholder("Ask about this lecture..."),
      ).toBeVisible();
    },
  );
});
