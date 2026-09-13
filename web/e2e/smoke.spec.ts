import { expect, test } from "@playwright/test";

test("chat renders and runs the scripted demo end-to-end", async ({ page }) => {
  await page.goto("/ui/");

  await expect(page.getByText("Dial in your")).toBeVisible();
  await page.getByRole("button", { name: "View a scripted demo" }).click();

  // The demo's closing line arrives (scripted, offline).
  await expect(page.getByText("That's the one change working")).toBeVisible({ timeout: 30_000 });

  // The research ledger and the approval card appear.
  await expect(page.getByText("Bonanza Coffee Roasters", { exact: true })).toBeVisible();
  const approve = page.getByRole("button", { name: "Approve & upload" });
  await expect(approve).toBeVisible();
  await approve.click();
  await expect(page.getByText("Approved and deployed")).toBeVisible();

  // The activity rail records tool spans.
  await expect(page.getByText("propose_next_action").first()).toBeVisible();
});

test("history page shows both shot charts and the comparison", async ({ page }) => {
  await page.goto("/ui/history");

  await expect(page.getByText("Shot #1042 vs #1043")).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText("#1042", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("#1043", { exact: true }).first()).toBeVisible();
});

test("events page streams domain events", async ({ page }) => {
  await page.goto("/ui/events");
  await expect(page.getByText("Waiting for events")).toBeVisible();
});

test("shots page rating saves feedback and shows the one change", async ({ page }) => {
  await page.goto("/ui/history");

  await page.getByRole("button", { name: "Rate this shot" }).first().click();

  await expect(page.getByText("Save rating")).toBeVisible();
  await expect(page.getByRole("slider", { name: "Acidity" })).toBeVisible();

  await page.getByRole("button", { name: "Save rating" }).click();

  await expect(page.getByText("One change · next pull")).toBeVisible({ timeout: 20_000 });
});
