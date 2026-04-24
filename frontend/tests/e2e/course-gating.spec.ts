import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

function escapeRegex(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function futureDate(daysAhead: number) {
  const date = new Date();
  date.setDate(date.getDate() + daysAhead);
  return date.toISOString().split("T")[0];
}

async function createLearnerWithAssessableTopic(
  request: APIRequestContext,
  label: string,
) {
  const email = `e2e-gating-${label}-${Date.now()}@example.com`;
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
  };

  const sectionsResponse = await request.get("http://127.0.0.1:8000/api/course-sections");
  expect(sectionsResponse.ok()).toBeTruthy();

  const sections = (await sectionsResponse.json()) as Array<{ id: string; title: string }>;

  for (const section of sections) {
    const detailResponse = await request.get(
      `http://127.0.0.1:8000/api/course-sections/${section.id}`,
    );
    expect(detailResponse.ok()).toBeTruthy();

    const detail = (await detailResponse.json()) as {
      title: string;
      learning_units: Array<{ id: string; canonical_unit_id: string | null; title: string }>;
    };

    for (const unit of detail.learning_units) {
      if (!unit.canonical_unit_id) continue;

      const assessmentStart = await request.post(
        "http://127.0.0.1:8000/api/assessment/start",
        {
          headers: {
            Authorization: `Bearer ${tokens.access_token}`,
          },
          data: {
            canonical_unit_ids: [unit.canonical_unit_id],
          },
        },
      );

      if (assessmentStart.ok()) {
        return {
          email,
          password,
          moduleName: detail.title,
          topicName: unit.title,
        };
      }
    }
  }

  throw new Error("No assessable topic found for e2e gating test.");
}

async function persistAuthenticatedUser(
  page: Page,
  request: APIRequestContext,
  tokens: {
    access_token: string;
    refresh_token: string;
    expires_in: number;
  },
) {
  const me = await request.get("http://127.0.0.1:8000/api/users/me", {
    headers: {
      Authorization: `Bearer ${tokens.access_token}`,
    },
  });
  expect(me.ok()).toBeTruthy();
  const user = await me.json();

  const expiresAt = String(Date.now() + tokens.expires_in * 1000);
  const cookiePairs = [
    { name: "al_access_token", value: tokens.access_token },
    { name: "al_refresh_token", value: tokens.refresh_token },
    { name: "al_token_expires_at", value: expiresAt },
  ] as const;

  await page.context().addCookies(
    cookiePairs.flatMap((cookie) => [
      { ...cookie, url: "http://127.0.0.1:3000" },
      { ...cookie, url: "http://localhost:3000" },
    ]),
  );

  await page.addInitScript((persistedUser) => {
    window.localStorage.setItem(
      "al-auth",
      JSON.stringify({
        state: { user: persistedUser },
        version: 0,
      }),
    );
  }, user);

  return user;
}

async function registerAuthenticatedLearner(
  page: Page,
  request: APIRequestContext,
  label: string,
  opts?: { onboard?: boolean },
) {
  const email = `e2e-catalog-${label}-${Date.now()}@example.com`;
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

  if (opts?.onboard) {
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
  }

  const user = await persistAuthenticatedUser(page, request, tokens);

  return { email, password, user, tokens };
}

async function seedRecommendedCourses(
  request: APIRequestContext,
  accessToken: string,
  courseSlugs: string[],
) {
  const response = await request.post(
    "http://127.0.0.1:8000/api/test-support/course-recommendations",
    {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
      data: {
        course_slugs: courseSlugs,
      },
    },
  );

  expect(response.ok()).toBeTruthy();
}

async function completeAssessment(page: Page) {
  for (let i = 0; i < 8; i += 1) {
    await expect(page.getByRole("radiogroup", { name: "Lựa chọn" })).toBeVisible();
    await page.getByRole("radio").first().click();

    const actionButton = page.getByRole("button", {
      name: /Câu tiếp|Nộp bài/,
    });
    const buttonLabel = (await actionButton.textContent())?.trim() ?? "";
    await actionButton.click();

    if (buttonLabel.includes("Nộp bài")) {
      await page.waitForURL(/\/assessment\/results/, { timeout: 15000 });
      return;
    }
  }

  throw new Error("Assessment flow did not reach the results page.");
}

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

  test("login -> onboarding -> assessment returns learner to the requested course", async ({
    page,
    request,
  }) => {
    const learner = await createLearnerWithAssessableTopic(request, "return-flow");

    await page.goto("/courses/cs231n");
    await page.getByRole("button", { name: "Start learning" }).click();
    await page.waitForURL(/\/login/);

    await page.getByLabel("Email").fill(learner.email);
    await page.locator('input[name="password"]').fill(learner.password);
    await page.getByRole("button", { name: "Đăng nhập" }).click();

    await page.waitForURL(/\/onboarding/);
    await page
      .getByRole("button", {
        name: new RegExp(escapeRegex(learner.topicName)),
      })
      .click();
    await page.getByRole("button", { name: "Tiếp theo" }).click();

    await page
      .getByRole("button", {
        name: new RegExp(escapeRegex(learner.moduleName)),
      })
      .click();
    await page.getByRole("button", { name: "Tiếp tục" }).click();

    await page.locator('input[type="date"]').fill(futureDate(30));
    await page.getByRole("button", { name: "Tiếp tục" }).click();

    await page.getByText("Xem video").click();
    await page.getByRole("button", { name: "Bắt đầu đánh giá" }).click();

    await page.waitForURL(/\/assessment/);
    await completeAssessment(page);

    const learningPathButton = page.getByRole("button", { name: "Xem lộ trình học" });
    await expect(page.getByText("Assessment hoàn thành!")).toBeVisible();
    await expect(learningPathButton).toBeVisible();
    await expect(learningPathButton).toBeEnabled();
    await learningPathButton.scrollIntoViewIfNeeded();
    await learningPathButton.click({ trial: true });
    await learningPathButton.click();

    await page.waitForURL(/\/courses\/cs231n\/learn\/lecture-1-introduction/, {
      timeout: 20000,
    });
    await expect(
      page.getByText("Framing CS231n within AI, machine learning, and deep learning").first(),
    ).toBeVisible();
  });
});

test.describe("US2: personalized catalog after skill test", () => {
  test("authenticated user with completed skill test sees recommended and all-courses tabs", async ({
    page,
    request,
  }) => {
    const learner = await registerAuthenticatedLearner(page, request, "recommended-tabs", {
      onboard: true,
    });
    await seedRecommendedCourses(request, learner.tokens.access_token, ["cs231n"]);

    await page.goto("/");

    await expect(page.getByRole("tablist")).toBeVisible();
    await expect(page.getByRole("tab", { name: "Recommended for you" })).toBeVisible();
    await expect(page.getByRole("tab", { name: "All courses" })).toBeVisible();
    await expect(
      page.getByRole("tab", { name: "Recommended for you" }),
    ).toHaveAttribute("aria-selected", "true");
    await expect(page.getByText("CS231n: Deep Learning for Computer Vision")).toBeVisible();
  });

  test("authenticated user without recommendations sees all-courses without tabs", async ({
    page,
    request,
  }) => {
    await registerAuthenticatedLearner(page, request, "no-recommendations");

    await page.goto("/");

    await expect(page.getByRole("tablist")).not.toBeVisible();
    await expect(page.getByText("CS231n: Deep Learning for Computer Vision")).toBeVisible();
    await expect(
      page.getByText("CS224n: Natural Language Processing with Deep Learning"),
    ).toBeVisible();
  });
});
