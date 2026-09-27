# React Frontend — UC-01 to UC-12 Coverage Plan

**Date:** 2026-09-27  
**Status:** FRONTEND FUNCTIONAL COVERAGE BASELINE  
**Backend:** V4.0 frozen; no backend redesign authorized  
**Source functional baseline:** `docs/USE_CASES_INVESTMENT_OPTIONS_V2.0.md`

## 1. Goal

Ensure every approved use case UC-01 through UC-12 is explicitly represented, testable and traceable in the production React frontend.

The frontend remains a presentation/client layer. It must not duplicate deterministic/statistical investment logic.

## 2. Recommended information architecture

Do not create twelve unrelated top-level pages. Group closely related use cases into coherent workspaces while preserving explicit UC traceability.

```text
Overview
Portfolio                    -> UC-01
Options                      -> UC-02
Opportunities                -> UC-03
Strategy Lab                 -> UC-04
Market Intelligence
  ├─ Regime                  -> UC-05
  ├─ Factors                 -> UC-06
  └─ Research & Events       -> UC-10
History & Learning
  ├─ Operations              -> UC-07
  ├─ Learnings               -> UC-08
  └─ Similarity              -> UC-09
Risk & Stress                -> UC-11
Copilot                      -> UC-12
```

This keeps the navigation understandable while making all twelve use cases first-class frontend capabilities.

## 3. Use case coverage matrix

| UC | Frontend surface | Required presentation | Current shell status | Frontend action |
|---|---|---|---|---|
| UC-01 Portfolio Intelligence | Portfolio | positions, avg cost, price, market value, P&L, concentration, cash semantics, assignment capital, obligations, risk, portfolio impact | Named page exists | BUILD canonical cards/table/drill-down |
| UC-02 Options Lifecycle | Options | type, underlying, strike, expiration, DTE, premium, price, IV/Greeks, moneyness, coverage, assignment, P&L, alternatives | Named page exists | BUILD positions + live chain + lifecycle detail |
| UC-03 Opportunity Discovery | Opportunities | canonical ranked universe, capital requirement, liquidity, risk, portfolio impact, deterministic score, prior experience, evidence | Named page exists | BUILD filters, ranking table and opportunity detail |
| UC-04 Strategy Comparison & What-if | Strategy Lab | side-by-side strategies, payoff, capital usage, assumptions, scenario impact, opportunity cost, historical evidence | No explicit surface | ADD Strategy Lab page/workspace |
| UC-05 Market & Regime | Market Intelligence / Regime | regime, trend, volatility, drawdown, rates, FX, commodities, flow, relevant events, as-of | Market Regime page exists | EVOLVE into Market Intelligence workspace |
| UC-06 Contextual Factor Intelligence | Market Intelligence / Factors | tested factors, association strength, effect size where available, sample, validation status, holdout/walk-forward evidence, caveat against causality | No explicit surface | ADD Factors tab with LIMITED handling |
| UC-07 Historical Operation Reconstruction | History & Learning / Operations | operation timeline, entry/during/exit feature snapshots, outcome, PIT provenance, source transactions | No explicit surface | ADD Operations tab and operation detail |
| UC-08 Experience & Continuous Learning | History & Learning / Learnings | lifecycle status, confidence, sample size, support/contradiction, recent vs long-term, drift, last confirmation, provenance | Named page exists | BUILD learning table/detail; support LIMITED state |
| UC-09 Historical Similarity | History & Learning / Similarity | comparable states/operations, feature similarity, regime similarity, semantic/temporal relevance, outcome and differences | Named page exists | BUILD ranked precedents with explainability |
| UC-10 Research / News / Events | Market Intelligence / Research & Events | event stream, affected assets/positions/learnings, confirm/contradict/no-impact classification, freshness and sources | No explicit surface | ADD Research & Events tab |
| UC-11 Risk / Scenario / Stress | Risk & Stress | scenario definition, portfolio P&L impact, option impact, assignment capital, concentration, liquidity, sensitivities, assumptions | Named page exists | BUILD scenario input + canonical result surfaces |
| UC-12 Decision Rationale / Copilot | Copilot + contextual drawer | rationale, deterministic facts, regime, portfolio/options context, precedents, learnings, evidence for/against, uncertainty, missing information, as-of | Named page exists | BUILD structured answer rendering; never raw JSON only |

## 4. Cross-cutting frontend contract

Every analytical screen must support the same metadata contract where available:

- `as_of` / freshness;
- quality status;
- provenance/source refs;
- evidence refs;
- deterministic vs generated/explanatory distinction;
- assumptions;
- limitations;
- UNKNOWN values shown explicitly;
- LIMITED / insufficient-history state;
- loading, error and empty state;
- no client-side inference of missing financial values.

## 5. LIMITED use cases in current runtime

The runtime-verified freeze records:

- **UC-06 LIMITED** — insufficient persisted multi-factor real history for calibrated live study;
- **UC-08 LIMITED** — insufficient finalized real outcomes;
- **UC-09 LIMITED** — insufficient accumulated real experience candidates.

Frontend requirement:

These pages must still exist and be production-quality. They must show a clear **Insufficient history / LIMITED** state with the reason, current sample/coverage when available, and which information is missing. The UI must not fabricate a score, learning or precedent.

## 6. Detail expectations by workspace

### Portfolio — UC-01

Top summary:
- total portfolio market value when canonical;
- available/unknown cash status;
- capital committed;
- assignment capital;
- number of stock and option positions;
- concentration/risk flags.

Main table:
- ticker;
- instrument;
- quantity;
- average cost;
- current price;
- market value;
- unrealized/realized P&L;
- weight;
- sector/issuer where available;
- obligations/coverage.

Detail:
- provenance;
- as-of;
- risk context;
- impact of candidate operation when supplied by backend.

### Options — UC-02

Views:
- current positions;
- live option chain;
- lifecycle/expiration;
- coverage/assignment;
- PUT/CALL analysis;
- Greeks/IV when provided;
- historical outcome link where available.

Never infer missing Greeks or IV.

### Opportunities — UC-03

Table:
- underlying/option;
- strategy;
- deterministic score;
- capital required;
- return/economic metrics;
- liquidity;
- portfolio impact;
- risk;
- quality.

Detail drawer:
- score components;
- assumptions;
- evidence/source refs;
- historical experience context;
- rejected/quality reasons.

### Strategy Lab — UC-04

Inputs are selections, not calculation logic.

UI:
- strategy A / B / N;
- current position or candidate opportunity;
- canonical scenario assumptions;
- side-by-side economics;
- payoff/capital/risk/portfolio impact;
- historical evidence;
- explicit distinction between facts, assumptions and qualitative rationale.

### Market Intelligence — UC-05, UC-06, UC-10

Tabs:

**Regime**
- regime dimensions;
- trend;
- volatility;
- rates;
- FX;
- commodities;
- flow;
- freshness.

**Factors**
- factor;
- asset/strategy scope;
- relationship metric;
- effect size when available;
- sample size;
- statistical validation;
- holdout/walk-forward stability;
- status;
- caveat: association != causality.

**Research & Events**
- timestamp/publication time;
- source;
- entity/event;
- affected asset/position/learning;
- support/contradict/update/no material impact;
- PIT eligibility;
- source link/ref.

### History & Learning — UC-07, UC-08, UC-09

Tabs:

**Operations**
- reconstructed operation list;
- open/close state;
- entry/during/exit snapshots;
- outcome;
- provenance.

**Learnings**
- lifecycle badge;
- confidence;
- sample;
- recent vs long-term evidence;
- supporting/contradicting observations;
- regime;
- drift;
- valid period;
- last confirmation;
- versions/supersession.

**Similarity**
- ranked historical precedents;
- feature similarity;
- regime similarity;
- semantic relevance;
- recency contribution;
- outcome;
- important differences from current context.

### Risk & Stress — UC-11

Scenario selector/input only sends assumptions to backend.

Results:
- portfolio P&L impact;
- per-position impact;
- option/assignment exposure;
- capital requirement;
- concentration;
- liquidity implications;
- sensitivities;
- assumptions and validation status.

### Copilot — UC-12

Response should render structured sections rather than only raw JSON:

- conclusion/synthesis;
- deterministic facts;
- market regime;
- portfolio/options context;
- historical precedents;
- active learnings;
- supporting evidence;
- contradicting evidence;
- risks;
- uncertainty / missing data;
- provenance;
- as-of;
- human decision reminder.

No order-entry or execution controls.

## 7. Navigation changes required from current React shell

Current shell already has:

- Overview
- Portfolio
- Options
- Opportunities
- Market Regime
- Experience & Learning
- Historical Similarity
- Risk & Stress
- Copilot

Recommended production navigation:

```text
Overview
Portfolio
Options
Opportunities
Strategy Lab
Market Intelligence
History & Learning
Risk & Stress
Copilot
```

Subnavigation:

```text
Market Intelligence
  Regime | Factors | Research & Events

History & Learning
  Operations | Learnings | Similarity
```

This explicitly closes the current frontend presentation gaps for UC-04, UC-06, UC-07 and UC-10.

## 8. Frontend acceptance matrix

The React phase is not complete until all twelve use cases can be demonstrated from the UI.

Acceptance per UC:

1. Route/workspace reachable.
2. Loading state.
3. Backend error state.
4. Empty state.
5. UNKNOWN state where applicable.
6. LIMITED state where applicable.
7. Real canonical data rendering.
8. `as_of` visible.
9. quality/provenance visible.
10. no invented data.
11. no duplicated investment computation in React.
12. no trade execution control.

Additional UC-specific acceptance:

- UC-01 validated on the real 47-position BTG portfolio.
- UC-02 validated with current OPLAB chain.
- UC-03 ranked opportunities show deterministic components.
- UC-04 comparison separates assumptions from facts.
- UC-05 macro/regime freshness visible.
- UC-06 LIMITED status represented correctly until real history is sufficient.
- UC-07 reconstructed operation exposes PIT snapshots.
- UC-08 LIMITED status represented correctly until outcomes accumulate.
- UC-09 LIMITED status represented correctly until experience corpus accumulates.
- UC-10 events preserve publication/evidence timing.
- UC-11 scenario assumptions are explicit.
- UC-12 rationale exposes evidence/limitations and cannot execute trades.

## 9. Implementation order

Recommended large implementation blocks:

### Block A — Core portfolio decisions
- shared metadata/state components;
- UC-01 Portfolio;
- UC-02 Options;
- UC-03 Opportunities;
- UC-04 Strategy Lab.

### Block B — Market context
- UC-05 Regime;
- UC-06 Factors;
- UC-10 Research & Events;
- consolidated Market Intelligence workspace.

### Block C — Experience
- UC-07 Operations;
- UC-08 Learnings;
- UC-09 Similarity;
- consolidated History & Learning workspace.

### Block D — Decision support
- UC-11 Risk & Stress;
- UC-12 structured Copilot;
- Overview aggregation.

### Block E — Acceptance
- UC-01 through UC-12 real-data UI walkthrough;
- production build;
- frontend/backend smoke;
- responsive desktop validation;
- freeze frontend functional baseline.

## 10. Conclusion

All UC-01 through UC-12 can be fully contemplated without changing the frozen backend architecture.

The current React shell is a useful foundation but is not yet functionally complete. The primary presentation gaps are UC-04, UC-06, UC-07 and UC-10. The recommended navigation and workspace structure closes those gaps while avoiding twelve disconnected top-level screens.

The next frontend implementation should begin with shared metadata/status components and Block A: Portfolio + Options + Opportunities + Strategy Lab.
