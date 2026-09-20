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


test("Copilot exposes all golden conversational cases and calls the orchestrator", async ({ page }) => {
  let receivedBody: any = null;
  await page.route("**/orchestrate", async route => {
    if (route.request().method() === "POST") {
      receivedBody = route.request().postDataJSON();
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "PASS",
          result: {
            synthesis: {
              summary: "Resposta estruturada para validação do Copilot.",
              uncertainties: ["Condições de mercado podem mudar."],
            },
            decision_proposal: {
              action: "HUMAN_REVIEW",
              subject_id: "PORTFOLIO",
              thesis: "A decisão depende das evidências determinísticas disponíveis.",
              rationale: "Nenhuma ordem é executada pelo Copilot.",
              as_of: "2026-09-18",
            },
            risk_validation: {
              status: "PASS",
              reasons: [],
            },
            deterministic_context: {
              opportunity_set: {
                as_of: "2026-09-18",
                quality_status: "VALIDATED",
                ranking_policy_version: "1.0",
                ranked_opportunities: [
                  { opportunity_id: "SELL_PUT:PETRV300", ticker: "PETR4", action: "SELL_PUT", capital_requirement: 3000 }
                ],
              },
            },
            evidence: [{ source_ref: "fixture:BTG" }],
            portfolio_context: { quality_status: "VALIDATED", as_of: "2026-09-18" },
          },
          sources: ["fixture:BTG"],
          audit: [{ event: "risk_validated" }],
        }),
      });
    } else {
      await route.continue();
    }
  });

  await page.goto("/");
  await page.getByRole("button", { name: /Copilot/ }).click();

  for (const id of ["GC-C01", "GC-C02", "GC-C03", "GC-C04", "GC-C05", "GC-C06", "GC-C07", "GC-C08"]) {
    await expect(page.getByText(id, { exact: false })).toBeVisible();
  }

  await page.getByText("GC-C01", { exact: false }).first().click();
  await page.getByRole("button", { name: "Enviar ao Orchestrator" }).click();

  await expect(page.getByText("Resposta estruturada para validação do Copilot", { exact: false })).toBeVisible();
  await expect(page.getByText("PASS", { exact: true })).toBeVisible();
  await expect(page.getByText("REQUIRED", { exact: true })).toBeVisible();

  expect(receivedBody).not.toBeNull();
  expect(receivedBody.task).toContain("R$ 80 mil");
  expect(receivedBody.context.client).toBe("react-dashboard-copilot");
  expect(receivedBody.context.surface).toBe("copilot");
  expect(receivedBody.context.use_case_id).toBe("GC-C01");
});
