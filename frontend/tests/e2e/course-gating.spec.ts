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

  const modulesResponse = await request.get("http://127.0.0.1:8000/api/modules");
  expect(modulesResponse.ok()).toBeTruthy();

  const modules = (await modulesResponse.json()) as Array<{ id: string; name: string }>;

  for (const module of modules) {
    const detailResponse = await request.get(
      `http://127.0.0.1:8000/api/modules/${module.id}`,
    );
    expect(detailResponse.ok()).toBeTruthy();

    const detail = (await detailResponse.json()) as {
      name: string;
      topics: Array<{ id: string; name: string }>;
    };

    for (const topic of detail.topics) {
      const assessmentStart = await request.post(
        "http://127.0.0.1:8000/api/assessment/start",
        {
          headers: {
            Authorization: `Bearer ${tokens.access_token}`,
          },
          data: {
            topic_ids: [topic.id],
          },
        },
      );

      if (assessmentStart.ok()) {
        return {
          email,
          password,
          moduleName: detail.name,
          topicName: topic.name,
        };
      }
    }
  }

  throw new Error("No assessable topic found for e2e gating test.");
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

    await expect(page.getByText("Assessment hoàn thành!")).toBeVisible();
    await page.getByRole("button", { name: "Xem lộ trình học" }).click();

    await page.waitForURL(/\/courses\/cs231n\/learn\/lecture-1-introduction/, {
      timeout: 20000,
    });
    await expect(page.getByText("Lecture 1: Introduction")).toBeVisible();
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
