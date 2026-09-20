import { test, expect } from "@playwright/test";
import path from "node:path";

test("dashboard reads BTG snapshot through orchestrator", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Valor Total", { exact: true })).toBeVisible();
  await expect(page.getByText("PETR4", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Fonte BTG", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: /Options/ }).click();
  await page.getByRole("button", { name: "Atualizar análise" }).click();
  await expect(page.getByText("Dados reais carregados via orquestrador", { exact: true })).toBeVisible();
  await expect(page.getByText("PETRV300", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: /Portfolio Intelligence/ }).click();
  await expect(page.getByText("Dados reais via Orchestrator", { exact: true })).toBeVisible();
  await expect(page.getByText("PETR4", { exact: true }).first()).toBeVisible();
});

test("dashboard upload buttons use orchestrator contracts", async ({ page }) => {
  await page.goto("/");

  const portfolioInput = page.locator('input[type="file"][accept=".xlsx,.xlsm"]').nth(0);
  await portfolioInput.setInputFiles(path.resolve("..", ".ci-data", "portfolio-upload.xlsx"));
  await expect(page.getByRole("status")).toContainText("snapshot anterior substituído");

  const optionsInput = page.locator('input[type="file"][accept=".xlsx,.xlsm"]').nth(1);
  await optionsInput.setInputFiles(path.resolve("..", ".ci-data", "options-upload.xlsx"));
  await expect(page.getByRole("status")).toContainText("snapshot anterior substituído");

  const noteInput = page.locator('input[type="file"][accept=".pdf"]');
  await noteInput.setInputFiles(path.resolve("..", ".ci-data", "nota-corretagem.pdf"));
  await expect(page.getByRole("status")).toContainText("nota de corretagem recebida");
});
