# ADR 0002 — Investment Price Policy

- **Status:** Accepted
- **Date:** 2026-09-14
- **Decision type:** C7 — Decision methodology

## Context

The valuation engines produce Bear/Base/Bull fair-value scenarios. The architecture requires a separate Investment Price Policy so valuation answers **quanto vale** while policy answers **a que preço a estratégia aceita acumular, reduzir ou vender**.

The policy must remain deterministic, explicit, auditable, and independent from LLM reasoning.

## Decision

Use the following default price-policy translation:

- **Accumulation Price** = `Base Fair Value × (1 − Margin of Safety)`
- **Reduce Price** = `Base Fair Value`
- **Sell Price** = `Bull Fair Value`

The margin of safety is an explicit policy input in the interval `[0, 1)`.

When a current market price is supplied, calculate the current margin of safety as:

`(Base Fair Value − Current Price) / Base Fair Value`

The policy must preserve the underlying Bear/Base/Bull valuation values and all source/audit fields. Policy assumptions are recorded explicitly in `ValuationRange.assumptions`.

## Rationale

1. Accumulation requires a discount to the central fair-value estimate.
2. The Base Fair Value is the neutral threshold at which reduction can be considered.
3. The Bull Fair Value represents the optimistic valuation boundary at which selling becomes a policy consideration.
4. The thresholds are policy outputs, not automatic trading instructions.
5. The Investment Committee and Risk Validation remain responsible for the final decision; valuation/policy does not autonomously execute BUY or SELL.

## Consequences

The same valuation can be evaluated under different investor risk preferences by changing the explicit margin-of-safety parameter without changing the valuation method itself.

The policy is deterministic and requires no LLM call.

The policy does not imply that reaching a threshold forces liquidation or purchase. It supplies auditable decision thresholds for later ranking and committee reasoning.

## Validation

Unit tests cover threshold calculation, current margin-of-safety calculation, audit-field preservation, invalid margins, and invalid current prices.

CI must remain green before this methodology is considered frozen.
