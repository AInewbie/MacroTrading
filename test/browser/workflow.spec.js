import { test, expect } from "@playwright/test";

test("source review → new theme → market review → portfolio → evaluation → report", async ({
  page,
  request,
}, info) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Overview", exact: true }),
  ).toBeVisible();
  async function navigate(name) {
    const menu = page.locator("#menu");
    const target = page.getByRole("link", { name, exact: true });
    if (info.project.name === "mobile") await menu.click();
    await target.click();
  }
  await navigate("Theme discovery");
  await page.getByRole("button", { name: "Screen source headlines" }).click();
  await page
    .getByRole("button", { name: "Review & accept unscored" })
    .first()
    .click();
  const id = "browser-theme-" + info.project.name;
  await page.getByLabel("New stable theme ID").fill(id);
  await page
    .getByLabel("Review reason")
    .fill("Review synthetic evidence for browser acceptance test.");
  await page.getByRole("button", { name: "Validate & save" }).click();
  await expect(page.locator("#notice")).toContainText(
    "New theme accepted unscored",
  );
  await navigate("Market data");
  await page
    .getByRole("combobox", { name: "Research theme", exact: true })
    .selectOption(id);
  await page.getByRole("button", { name: "Fetch reference history" }).click();
  await page
    .getByRole("button", { name: "Review proxy & accept history" })
    .click();
  await page
    .getByLabel("Review reason")
    .fill("Review synthetic reference fixture and proxy mapping.");
  await page.getByRole("button", { name: "Validate & save" }).click();
  await expect(page.locator("#notice")).toContainText("history accepted");
  await page.screenshot({
    path: `test-results/${info.project.name}-market.png`,
    fullPage: true,
  });
  await navigate("Portfolio risk");
  await page
    .getByRole("button", { name: "Calculate portfolio impact" })
    .click();
  await expect(
    page.getByRole("heading", { name: "Scenario assumptions & attribution" }),
  ).toBeVisible();
  await expect(
    page.getByText("Pre-trade checks", { exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: `test-results/${info.project.name}-risk.png`,
    fullPage: true,
  });
  await navigate("Evaluation");
  await page.getByRole("button", { name: "Load portfolio example" }).click();
  await page.getByRole("button", { name: "Validate & save" }).click();
  await expect(
    page.getByRole("heading", { name: "Portfolio results" }),
  ).toBeVisible();
  await page.screenshot({
    path: `test-results/${info.project.name}-evaluation.png`,
    fullPage: true,
  });
  await navigate("Run archive");
  const href = await page
    .getByRole("link", { name: "HTML report ↗" })
    .first()
    .getAttribute("href");
  const report = await request.get(href);
  expect(report.ok()).toBeTruthy();
  expect(await report.text()).toContain("Reproduction manifest");
  const blueprint = await request.get("/api/blueprint");
  expect(blueprint.ok()).toBeTruthy();
  const pages = [
    "Overview",
    "Research themes",
    "Sources & evidence",
    "Portfolio",
    "Paper orders",
    "Decision journal",
    "All data",
    "Settings",
  ];
  for (const name of pages) {
    await navigate(name);
    await expect(page.locator("#page-title")).toHaveText(name);
  }
  expect(errors).toEqual([]);
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth + 2,
  );
  expect(overflow).toBeFalsy();
  await page.screenshot({
    path: `test-results/${info.project.name}-settings.png`,
    fullPage: true,
  });
});
