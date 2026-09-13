# Upstream Architecture Review — TradingAgents v0.4.2

**Reference:** TauricResearch/TradingAgents  
**Frozen commit:** `be952b8eccb49720509af544c6675233bc1f10d0`  
**Review date:** 2026-09-13  
**Status:** Reference-only; no upstream source modification permitted

## 1. Executive conclusion

TradingAgents v0.4.2 is a mature LangGraph-based multi-agent framework. Its strongest reusable ideas for the B3 Investment & Options Agent are:

- explicit graph/state separation;
- conditional routing and bounded debate loops;
- structured LLM outputs using Pydantic schemas;
- checkpoint/resume support;
- point-in-time-aware memory/outcome resolution;
- provider abstraction and configurable model selection;
- explicit separation of analyst, research, risk and portfolio stages.

The framework is **not** adopted wholesale. Its core design is optimized for LLM-heavy multi-agent trading/research. Our approved architecture remains:

> **Python-first → Local-first → LLM-for-reasoning**

The B3 system additionally requires first-class deterministic engines for valuation, options, portfolio context and opportunity ranking. These are not responsibilities to delegate to an LLM.

## 2. Upstream graph architecture

The upstream graph starts with a configurable sequence of market/social/news/fundamentals analysts. Analyst nodes can call tools, then pass through message-clear nodes. Research then enters a Bull Researcher ↔ Bear Researcher debate, followed by Research Manager, Trader, and a three-way Aggressive/Neutral/Conservative risk debate before Portfolio Manager terminates the graph.

This structure is implemented in `tradingagents/graph/setup.py` and routed by `ConditionalLogic`.

**Reusable:** graph construction patterns, conditional routing, bounded discussion loops.  
**Not reusable as-is:** the exact analyst/debate topology and its assumption that repeated LLM discussion is the primary reasoning mechanism.

## 3. State model

`AgentState` extends LangGraph `MessagesState` and carries instrument identity, trade date, analyst reports, investment debate state, trader plan, risk debate state, final trade decision and past context.

**Reusable:** typed state, explicit run date, deterministic instrument context, separation of debate states.  
**Required B3 change:** introduce strongly typed state for stock valuation, PUT/CALL opportunities, portfolio state, opportunity ranking, risk validation and decision provenance.

## 4. Structured outputs

The upstream framework defines Pydantic schemas for decision-producing agents such as Research Manager, Trader and Portfolio Manager. Provider-native structured-output mechanisms are used where possible, and renderers preserve human-readable Markdown compatibility.

**Reusable:** Pydantic-first contracts, enum-constrained decisions, validation, deterministic rendering.  
**B3 extension:** structured schemas must represent actions such as BUY/ACCUMULATE, SELL PUT, HOLD, SELL CALL, REDUCE, SELL, WAIT and AVOID, plus strike, expiry, premium, effective acquisition/sale price, opportunity cost, confidence, evidence, thesis and invalidation conditions.

## 5. Configuration and model abstraction

`default_config.py` centralizes environment overrides, provider/model selection, debate depth, checkpointing, data vendor selection and retry/output-token controls. `trading_graph.py` creates provider-specific LLM clients and separates quick/deep thinking models.

**Reusable:** one configuration source, model abstraction, provider-specific parameters, explicit retry/token settings.  
**B3 change:** configuration must also cover B3 data providers, market calendar, point-in-time policy, option liquidity thresholds, valuation assumptions, portfolio constraints, LLM gate thresholds and cost budgets.

## 6. Memory and point-in-time behavior

The upstream `TradingMemoryLog` stores decisions in an append-only Markdown log and later resolves outcomes. Historical context can be filtered by the date when an outcome became known, preventing backtests from seeing future outcomes. This is a strong pattern and should be preserved conceptually.

**Reusable:** append-only decision history, outcome resolution, idempotency, atomic updates, explicit `resolved` date and historical cutoff.

**B3 implementation:** authoritative structured memory belongs in SQLite/Parquet. Obsidian is the human-editable semantic memory/policy layer. RAG retrieves only relevant notes. No whole-vault prompt injection.

## 7. Data and tool architecture

The upstream framework exposes abstract tool methods for stock data, indicators, fundamentals, statements, news, macro data, insider activity, prediction markets and market verification. yfinance is the default core vendor in the provided configuration.

**Reusable:** provider abstraction, deterministic verification layer, cached data and explicit vendor configuration.

**B3 change:** data acquisition must be designed around Brazilian equities and options, including B3-specific symbols, corporate actions, dividends, option chains, strikes, expiries, open interest, volume, bid/ask, IV and Greeks. Point-in-time snapshots are mandatory for backtesting.

## 8. Checkpointing and run identity

The upstream graph supports checkpoint/resume and includes graph-shape inputs in a run signature so incompatible runs do not silently resume the wrong graph.

**Reusable and recommended:** yes. Our LangGraph flow should preserve explicit run signatures and prevent invalid checkpoint continuation after changes in graph shape, analyst selection, strategy mode or asset type.

## 9. What we will reuse

1. LangGraph as orchestration/state machine.
2. Typed state and structured Pydantic contracts.
3. Conditional routing with bounded loops.
4. Provider/model abstraction.
5. Checkpoint/resume with configuration/run signatures.
6. Point-in-time memory cutoff concept.
7. Deterministic rendering of structured decisions.
8. Test discipline around graph behavior and look-ahead protection.

## 10. What we will not copy

1. The full LLM analyst/debate topology.
2. LLM calls for deterministic technical/fundamental calculations.
3. Generic US-centric assumptions as the basis for B3 analysis.
4. Markdown as the authoritative structured data store.
5. Automatic trade execution in early phases.
6. Free-form model output as the primary decision contract.

## 11. Architectural mapping

| Upstream concept | B3 architecture | Decision |
|---|---|---|
| LangGraph | LangGraph | Reuse |
| AgentState | B3 typed state | Adapt |
| Analyst tools | Data/Quant engines | Redesign |
| Research debate | Investment Committee | Reduce/adapt |
| Trader | Opportunity/Decision layer | Redesign |
| Risk debate | Risk Validator | Redesign |
| Portfolio Manager | Portfolio Context + Decision | Redesign |
| Structured schemas | B3 decision schemas | Reuse/adapt |
| Markdown memory log | SQLite/Parquet + Obsidian | Replace |
| yfinance-centric data | B3 data layer | Replace/extend |
| Quick/deep LLMs | LLM Gateway + model escalation | Adapt |
| Checkpointing | LangGraph checkpoint | Reuse |

## 12. Architecture guardrail

No upstream component is copied into production merely because it exists upstream. Any proposed reuse requires a change request and must answer the seven impact questions defined by project governance:

1. Does component responsibility change?
2. Does LangGraph flow change?
3. Does any interface change?
4. Is a new data source introduced?
5. Is a new LLM call introduced?
6. Is there look-ahead/data leakage risk?
7. Could an investment decision regress?

Architectural changes require an ADR.
