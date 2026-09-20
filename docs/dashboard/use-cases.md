# Dashboard Use Cases

## 1. Portfolio

Visualiza o snapshot oficial da carteira via Orchestrator.

**Estado:** IMPLEMENTADO e coberto por E2E.

## 2. Options Intelligence

Consulta transações, lifecycles e P&L determinístico via Orchestrator.

**Estado:** IMPLEMENTADO e coberto por E2E.

**Nota:** o novo ledger de corretagem ainda é uma fonte separada para fins de reconciliação; upload não implica alteração automática do P&L Excel.

## 3. Portfolio Intelligence

Apresenta exposição e contexto de capital/risco calculados pelo backend.

**Estado:** IMPLEMENTADO e coberto por E2E.

## 4. Brokerage note ingestion

Seleciona múltiplos PDFs, processa cada nota, persiste transações no ledger e registra o manifest.

**Estado:** IMPLEMENTADO e coberto por contrato/E2E.

## 5. Copilot — Golden Cases

| ID | Caso | UI/contrato automatizado | Workflow real pendente |
|---|---|---:|---:|
| C01 | Opportunity Discovery | Sim | Sim |
| C02 | Capital Insufficient | Sim | Sim |
| C03 | Diversification | Sim | Sim |
| C04 | Position vs Opportunity | Sim | Sim |
| C05 | BUY vs SELL PUT | Sim | Sim |
| C06 | Valuation | Sim | Sim |
| C07 | Existing PUT | Sim | Sim |
| C08 | Insufficient Evidence | Sim | Sim |

A suíte E2E confirma que C01–C08 aparecem e que C01 envia o contrato correto. A resposta do teste E2E é mockada; portanto isso não equivale a oito validações contra o workflow real.

## 6. Upload de portfolio

**Estado:** IMPLEMENTADO; contrato backend e E2E cobertos.

## 7. Upload de options transactions

**Estado:** IMPLEMENTADO; contrato backend e E2E cobertos.

## 8. Reconciliation

**Estado:** engine backend disponível; UI dedicada ainda não implementada.

Deve mostrar:
- cobertura por fonte;
- `current` vs `historical_only`;
- possíveis duplicidades;
- limites de cobertura.

## 9. Opportunities

**Estado:** PLACEHOLDER.

Deve consumir OpportunitySet/Opportunity Intelligence existente, sem copiar ranking/regras para TypeScript.

## 10. Knowledge

**Estado:** indicadores backend; UI dedicada ainda não implementada.

## 11. Ainda não cobertos como experiência funcional

- Ledger ↔ Options Excel integrado ao runtime;
- tela de reconciliação;
- Opportunities UI;
- Knowledge UI;
- C01–C08 contra workflow real;
- regressão com conjunto controlado de notas reais anonimizadas;
- histórico persistente do Copilot;
- Tauri desktop empacotado.

## Critério de conclusão

Um caso é concluído quando contrato, regra backend, testes, E2E quando aplicável e validação manual necessária estiverem registrados e a documentação refletir o comportamento real.
