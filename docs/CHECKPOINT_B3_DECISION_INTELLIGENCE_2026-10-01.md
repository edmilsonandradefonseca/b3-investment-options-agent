# CHECKPOINT — B3 Decision Intelligence — 2026-10-01

## Scope

Continue improving B3 Agent intelligence across the existing V4.3 architecture and approved UC-01..UC-12. **Do not redesign the backend.** The focus is to make Market Intelligence, Opportunities, Strategy Lab and Copilot use the deterministic/canonical data, historical operations, learning and reasoning that already exist.

Repository: `edmilsonandradefonseca/b3-investment-options-agent`

Integration branch: `feature/react-functional-v43-integration`

Draft PR: `#66`

Checkpoint HEAD: `8bd16db88073bd7168d02d5e295b1a3461892c41`

CI at checkpoint: `#1258 SUCCESS`

## Non-negotiable project principles

These principles are acceptance criteria for every future change:

1. **Evidence before conclusion** — Evidence precedes conclusions, recommendations and synthesis.
2. **Deterministic authority** — measurable facts, prices, positions, Greeks, P&L, scoring, risk and controls belong to deterministic engines/canonical stores.
3. **Canonical Evidence authority** — observed external facts are normalized with provenance, PIT, source class, materiality and identity; LLMs never rewrite Evidence.
4. **LLMs are not truth stores** — DeepSeek, Luna and Sol interpret/synthesize; their outputs are derived intelligence.
5. **OpenClaw/Luna never waits for DeepSeek** — senior reasoning receives canonical Evidence immediately and only consumes a local dossier when it is READY/current/valid.
6. **UNKNOWN remains UNKNOWN** — missing data never silently becomes zero or an assumption.
7. **Point-in-time correctness** — mandatory for B3; historical Open Data is never promoted to OBSERVED_LIVE.
8. **Human-in-the-loop** — B3 orders, spending, credentials, legal commitments and irreversible actions require human control.
9. **No small-LLM router** — Fast Router is code-only; ambiguity escalates to senior reasoning.
10. **Shared physical resources, isolated authority** — João and B3 may share infrastructure, but never domain authority.

Any proposed optimization must preserve these principles.

## Authoritative documentation to read first

- `docs/ARCHITECTURE_V4.3.md`
- `docs/USE_CASES_INVESTMENT_OPTIONS_V2.0.md`
- `docs/USE_CASE_ARCHITECTURE_TRACEABILITY_V2.0.md`
- `docs/FRONTEND_FUNCTIONAL_SPEC_V1.0.md`
- `docs/ARCHITECTURE_V4.0.md`
- `docs/ADR/0020-continuous-learning-experience-memory.md` when reviewing UC-07/08/09.

Do not reopen the V4.3 authority model unless a concrete defect requires an explicit amendment.

## Critical correction — historical truth already exists in SQLite

Brokerage notes have already been imported into SQLite.

**Do not create a new ledger, duplicate transaction table or parallel persistence model simply to implement historical intelligence.**

Known existing components:

- `src/b3_agent/repositories/option_ledger.py`
  - `OptionTransactionLedger`
  - runtime file: `<data_dir>/options.sqlite3`
  - existing table: `option_transactions`
- `src/b3_agent/options/brokerage_batch.py`
  - brokerage-note parser and idempotent ingestion
  - source manifest in `source_manifest.sqlite3`
- `src/b3_agent/repositories/transaction.py`
  - existing `transactions` repository/table
- `src/b3_agent/historical_operations.py`
- `src/b3_agent/continuous_learning.py`
- `src/b3_agent/historical_similarity.py`
- `src/b3_agent/orchestration/experience_workflow.py`

**First action in the next higher-resource session:** inspect the actual Ubuntu SQLite files, PRAGMA schemas, row counts, date ranges and representative rows. Reuse existing canonical truth. Prefer queries/read models/derived projections over new persistence.

## Current workspace responsibilities

### Market Intelligence

Primary UCs: UC-05, UC-06, UC-10.

Purpose: reusable market/asset context. It must not be a trade recommendation engine.

### Opportunities

Primary UC: UC-03.

Purpose: deterministic/canonical opportunity discovery. LLMs may interpret candidates but must never invent them.

### Strategy Lab

Primary UC: UC-04, consuming UC-01/02/03/05/07/08/09/10/11.

Purpose: compare explicit alternatives using the same facts, assumptions and provenance.

## Latest real acceptance

Command:

```bash
cd /opt/b3-investment-options-agent && \
git pull --ff-only origin feature/react-functional-v43-integration && \
sudo systemctl restart b3-runtime.service && \
./.venv/bin/python scripts/validate_market_covered_call_real.py
```

Result:

`PASS MARKET + OPTIONS + STOCK DECISIONS REAL`

Observed real results:

- Market Intelligence: 8 dated events after the live-PIT fix.
- Covered CALL candidate from the actual portfolio:
  - PCAR3
  - `PCARK375`
  - strike 3.75
  - bid 0.15
  - ask 0.24
  - 52,000 PCAR3 shares held
  - 100 shares needed for one covered contract.
- UC-03: 10 candidates, 9 covered CALL candidates.
- UC-03 ranking correctly remains `DEFERRED_INCOMPLETE_CONTEXT`.
- Covered position value is separately exposed from incremental capital:
  - covered position value: R$324
  - incremental capital required: R$0
- Strategy Lab stock-reduction what-if:
  - R$10,000 notional reduction
  - 52,000 shares before
  - 48,913.58 theoretical shares after
  - execution quantity remains `not_inferred`.

## Why the result is still not good enough

The technical path works, but decision intelligence remains shallow.

Examples:

- “Executable” is still not equivalent to liquid/attractive. The validated PCAR3 call had a wide spread.
- UC-03 still cannot produce a defensible economic ranking because valuation, calibrated liquidity, portfolio impact, risk and prior experience are incomplete.
- Historical experience is not yet deeply used by Opportunities/Strategy Lab/Copilot.
- Strategy Lab is still mostly mechanical economics rather than a complete comparison using history, learning, risk, opportunity cost and regime.
- João is connected, but past validation showed memory retrieval with zero items.
- DeepSeek local dossiers are often ABSENT, which is acceptable when no material event exists; do not force DeepSeek into the critical path.
- Full senior intelligence calls are slow (~80–95 s per workspace in prior tests).

## Historical intelligence requirement

The project specification already expects UC-07/08/09 to enrich decisions.

Target questions include:

- “Como foram minhas covered calls de PETR4 nos últimos 6 meses?”
- “Quantas expiraram OTM, quantas foram recompradas, exercidas/assigned ou roladas?”
- “Quando rolei uma CALL, qual foi o resultado econômico da cadeia completa?”
- “Qual foi minha frequência histórica de assignment em PUTs semelhantes?”
- “Esta operação atual se parece com quais operações anteriores?”
- “Minhas covered calls funcionaram melhor com IV alta ou baixa?”
- “Em regime semelhante ao atual, o que aconteceu nas minhas operações comparáveis?”

Historical observed frequencies are personal empirical frequencies, **not market probabilities**.

Before adding storage, inspect what can already be derived from:

- existing `option_transactions`;
- existing `transactions`;
- option contract metadata;
- expiry dates;
- current/historical underlying data;
- position changes around expiry;
- close/reopen sequences around rolls;
- existing operation/outcome/experience schemas.

Lifecycle classification should be improved only where deterministically supportable:

- OPEN
- CLOSED
- EXPIRED_OTM / worthless
- ASSIGNED
- EXERCISED
- ROLLED
- partial close / partial roll where evidence supports it.

Rolls should preserve predecessor/successor and whole-chain economics.

## Desired richer analysis

The same intelligence architecture should support PUT, CALL and stock decisions.

Example: “Analise venda de PUT RENT3 16/10.”

Desired canonical inputs where available:

- current OPLAB underlying quote + timestamp;
- current option chain, using current bid for sell economics;
- strike/DTE/moneyness;
- bid/ask/spread/volume/OI;
- IV/Greeks;
- premium yield/effective acquisition price;
- historical realized volatility;
- regime/factors;
- dated events and provenance;
- assignment capital and portfolio concentration;
- scenarios/stress;
- prior comparable personal operations;
- empirical expiry/assignment/roll frequencies;
- active learnings with sample size/confidence;
- supporting and contradicting evidence;
- limitations/UNKNOWNs.

Analogous treatment must work for:

- covered CALL;
- BUY/HOLD/REDUCE/SELL stock;
- close/hold/roll options;
- comparisons such as BUY stock vs SELL PUT or HOLD stock vs covered CALL.

Do not build a PUT-only architecture.

## LLM / latency optimization requirement

Improve speed **without weakening evidence quality or authority**.

Preferred direction:

1. deterministic/SQLite retrieval first;
2. one reusable context fingerprint per asset/as-of/portfolio state;
3. reuse market research, option chain, portfolio context and historical experience across nearby workspace requests;
4. do not repeat specialist/senior calls for identical context;
5. compact structured prompts, not huge raw payloads;
6. one senior synthesis where possible;
7. deterministic response first, derived intelligence afterward when useful;
8. DeepSeek stays async/background;
9. OpenClaw/Luna invoked only for real synthesis/ambiguity;
10. Fast Router stays code-only;
11. stage-level latency telemetry and cache hit/miss visibility;
12. preserve provenance, PIT and UNKNOWN semantics.

## Next session — required first deliverable

Before coding:

1. verify branch, current HEAD, PR #66 and CI;
2. read the authoritative docs listed above;
3. inspect the real SQLite runtime files and data coverage;
4. map existing repositories/services to UC-02/07/08/09;
5. produce a gap matrix with:
   - fully implemented;
   - implemented but not wired;
   - missing implementation;
   - missing real data;
   - frontend-only gap;
6. identify what can be solved with existing data and no schema change;
7. propose the smallest additive implementation plan;
8. only then change code;
9. batch changes, keep CI green and validate against the real Ubuntu instance using a small number of focused acceptance scripts.

## Anti-goals

- no backend redesign;
- no duplicate SQLite ledger/table by convenience;
- no financial business logic in React;
- no DeepSeek in the synchronous critical path;
- no numerical truth from João/OpenClaw/Luna;
- no silent UNKNOWN→0;
- no LLM-created opportunity;
- no annualized option return as sole ranking driver;
- no “executable = liquid/attractive” shortcut;
- no personal win rate represented as market probability;
- no autonomous order execution.
