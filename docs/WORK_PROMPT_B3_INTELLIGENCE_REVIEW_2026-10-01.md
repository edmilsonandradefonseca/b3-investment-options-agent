# PROMPT FOR CHATGPT WORK — B3 Agent Intelligence Completion

Continue the B3 Investment & Options Agent from the repository:

`edmilsonandradefonseca/b3-investment-options-agent`

Server runtime:

`/opt/b3-investment-options-agent`

Integration branch:

`feature/react-functional-v43-integration`

Draft PR:

`#66`

## Start here

Before modifying code:

1. Verify the **current** branch HEAD, PR state and CI in GitHub.
2. Read:
   - `docs/CHECKPOINT_B3_DECISION_INTELLIGENCE_2026-10-01.md`
   - `docs/ARCHITECTURE_V4.3.md`
   - `docs/USE_CASES_INVESTMENT_OPTIONS_V2.0.md`
   - `docs/USE_CASE_ARCHITECTURE_TRACEABILITY_V2.0.md`
   - `docs/FRONTEND_FUNCTIONAL_SPEC_V1.0.md`
   - `docs/ARCHITECTURE_V4.0.md`
   - `docs/ADR/0020-continuous-learning-experience-memory.md` if present.
3. Treat GitHub as source of truth for code.
4. Inspect the **actual Ubuntu SQLite files** before proposing schema or persistence changes.

At checkpoint time the branch HEAD was `8bd16db88073bd7168d02d5e295b1a3461892c41`, but do not assume it is still current.

## Mandatory project principles

Every recommendation and implementation must preserve:

- **Evidence before conclusion** — evidence precedes conclusions/recommendations/synthesis.
- **Deterministic authority** — prices, positions, Greeks, P&L, scoring, risk and controls belong to deterministic engines/canonical stores.
- **Canonical Evidence authority** — external facts are normalized with provenance, PIT, source class, materiality and identity; LLMs do not rewrite Evidence.
- **LLMs are not truth stores** — DeepSeek, Luna and Sol produce derived intelligence only.
- **OpenClaw/Luna never waits for DeepSeek** — canonical Evidence is immediately available to senior reasoning; local dossiers are consumed only when READY/current/valid.
- **UNKNOWN remains UNKNOWN** — no silent zero/default assumption.
- **Point-in-time correctness** — mandatory; historical Open Data is never OBSERVED_LIVE.
- **Human-in-the-loop** — no autonomous B3 orders, spending, credentials, legal commitments or irreversible actions.
- **No small-LLM router** — Fast Router remains code-only; ambiguity escalates to senior reasoning.
- **Shared physical resources, isolated authority** — João and B3 may share infrastructure, never domain authority.

Do **not** redesign V4.3 to solve missing wiring.

## Critical constraint: do not duplicate historical storage

The brokerage-note history is already loaded into SQLite.

Existing components include:

- `OptionTransactionLedger` in `src/b3_agent/repositories/option_ledger.py`;
- `<data_dir>/options.sqlite3`, table `option_transactions`;
- `TransactionRepository` / existing `transactions` table;
- `source_manifest.sqlite3`;
- brokerage-note archived/imported evidence;
- UC-07/08/09 services and schemas.

Do not create a new ledger or parallel historical tables just because it is convenient.

First inspect:

- SQLite files;
- PRAGMA table schemas;
- row counts;
- date coverage;
- representative records;
- how buy/sell direction is encoded;
- option ticker/strike/expiry/type derivation;
- source/note provenance.

Prefer queries, adapters, reconstruction services, read models and derived projections over new canonical persistence.

Only propose a schema change if you prove an essential canonical fact cannot be represented/derived from existing truth.

## Product objective

Increase real decision intelligence in the existing three workspaces.

### Market Intelligence — UC-05/06/10

Should answer:

> What is happening in the market/asset context that materially affects a decision?

Use deterministic market/regime/factor data and dated external Evidence with provenance.

### Opportunities — UC-03

Should answer:

> Which canonical actions are worth investigating now given market, portfolio, risk and historical experience?

Examples include:

- SELL PUT;
- covered SELL CALL;
- BUY/HOLD when valuation supports it;
- SELL/REDUCE held stock;
- close/roll when UC-02 lifecycle supports it.

LLMs may explain but never create candidates.

### Strategy Lab — UC-04

Should answer:

> How do explicit alternatives compare using the same facts and assumptions?

Examples:

- buy stock vs sell PUT;
- hold vs covered CALL;
- hold vs reduce/sell;
- hold/close/roll option;
- stock A vs stock B when canonical evidence supports it.

## Main missing intelligence: exploit past operations

The specification already requires historical reconstruction, learning and similarity.

The user should be able to ask:

- “Como foram minhas covered calls de PETR4 nos últimos 6 meses?”
- “Quantas expiraram OTM, quantas foram exercidas, recompradas ou roladas?”
- “Quando rolei uma CALL, qual foi o resultado da cadeia inteira?”
- “Qual foi minha frequência histórica de assignment em PUTs semelhantes?”
- “Esta opção atual se parece com quais operações anteriores?”
- “Minhas covered calls funcionaram melhor com IV alta ou baixa?”
- “Em regimes semelhantes ao atual, o que aconteceu?”

Review UC-07/08/09 implementation and determine why this information is not yet deeply contributing to UC-03/04/12.

Expected architecture:

`existing SQLite transaction truth → UC-07 reconstruction → finalized outcomes → UC-08 learning → UC-09 similarity → PRE-ANALYSIS context → UC-03/04/12 reasoning`

Historical empirical frequency is not a predictive market probability.

Inspect whether current reconstruction can already derive:

- OPEN;
- normal CLOSE;
- EXPIRED_OTM / worthless;
- ASSIGNED / EXERCISED;
- ROLLED;
- partial close / partial roll.

Use option contract metadata, expiry, transaction history, position changes and underlying state before asking for new storage.

For rolls, preserve predecessor/successor and whole-chain economics.

## Current real status

Latest real focused validation:

`PASS MARKET + OPTIONS + STOCK DECISIONS REAL`

Validated on real runtime:

- current market research;
- current OPLAB option data;
- covered CALL with actual held shares;
- UC-03 covered CALL candidate generation;
- Strategy Lab stock reduction what-if.

Observed real candidate:

- PCAR3;
- `PCARK375`;
- strike 3.75;
- bid 0.15;
- ask 0.24;
- 52,000 shares held;
- 100 shares required.

The path works but the intelligence is still insufficient.

Known gaps:

- poor spreads can still yield “executable” candidates;
- ranking remains `DEFERRED_INCOMPLETE_CONTEXT`;
- prior experience does not materially enrich the decision;
- risk/portfolio impact/valuation/liquidity are incomplete;
- stock reduction is still primarily mechanical;
- senior LLM path is slow.

## Deep review requested

Before coding, produce a concise gap matrix answering:

1. What is fully implemented?
2. What exists but is not wired?
3. What is specified but missing?
4. What is already in SQLite and should simply be queried/reconstructed?
5. What can be derived without schema changes?
6. What really requires code enhancement?
7. What needs additional external data?
8. What is frontend-only?
9. What specifically prevents UC-07/08/09 from enriching UC-03/04/12 today?
10. What is the smallest additive implementation that fixes this while respecting V4.3?

Then implement the smallest coherent package.

## Example quality target

For:

> “Analise venda de PUT RENT3 com vencimento em 16/10.”

The analysis should combine, when canonically available:

- current OPLAB stock quote and timestamp;
- current option chain with bid-based sell economics;
- strike/DTE/moneyness;
- bid/ask/spread/volume/OI;
- IV/Greeks;
- premium yield/effective acquisition price;
- realized volatility/history;
- market regime/factors;
- dated material events;
- portfolio assignment capital/concentration;
- scenario/stress evidence;
- relevant historical personal operations;
- observed assignment/expiry/roll frequencies;
- persistent learnings and sample confidence;
- similar precedents;
- supporting vs contradicting evidence;
- UNKNOWN/limitations.

The same intelligence pattern must support CALLs and stock buy/hold/reduce/sell decisions.

Do not create a PUT-only framework.

## LLM speed / cost optimization

Current senior paths can take ~80–95 seconds per workspace. Improve this additively.

Required principles for optimization:

1. SQLite/deterministic retrieval before LLM.
2. Build a reusable context fingerprint/snapshot from asset + as-of + portfolio + relevant Evidence.
3. Reuse market facts, option chain, historical experience and research across workspaces when the fingerprint/freshness allows.
4. Do not repeat specialist or senior calls for identical context.
5. Use compact structured slices, not giant raw prompts.
6. Prefer one senior synthesis over repeated full-context calls.
7. Return deterministic output quickly, then derived intelligence if needed.
8. DeepSeek remains async/background and never blocks.
9. OpenClaw/Luna used only for synthesis/ambiguity.
10. Fast Router remains code-only.
11. Preserve provenance/PIT/UNKNOWN semantics.
12. Add latency telemetry per stage and cache/reuse indicators.

Do not achieve speed by omitting necessary evidence.

## Execution style

Work autonomously and in coherent batches.

- Use GitHub for code checks.
- Inspect the live Ubuntu SQLite state before inventing persistence.
- Keep CI green.
- Prefer focused real-instance acceptance scripts.
- Do not make the user run many exploratory commands.
- Ask for one real validation command only after a coherent CI-green block is ready.
