import { expect, test } from "@playwright/test";

test("public users can discover demo courses and inspect overview states", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByText("Explore available courses")).toBeVisible();
  await expect(page.getByText("CS231n: Deep Learning for Computer Vision")).toBeVisible();
  await expect(
    page.getByText("CS224n: Natural Language Processing with Deep Learning"),
  ).toBeVisible();

  await page.getByRole("link", { name: "Open overview" }).first().click();
  await expect(
    page.getByRole("heading", { name: "Build deep intuition for modern vision systems" }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Start learning" })).toBeEnabled();

  await page.goto("/courses/cs224n");
  await expect(
    page.getByRole("heading", { name: "Explore modern NLP and language modeling workflows" }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Coming soon" })).toBeDisabled();
});
