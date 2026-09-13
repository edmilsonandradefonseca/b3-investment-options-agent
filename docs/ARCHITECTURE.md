# Architecture Governance — B3 Investment & Options Agent

## 1. Architectural baseline

This repository implements a personal investment decision-support system for B3. It is **not** an autonomous trading system.

The approved architectural principle is:

> **Python-first, local-first, LLM-for-reasoning.**

Deterministic computation must not be delegated to an LLM when it can be performed reliably by code.

## 2. Approved high-level architecture

B3 Market/Data Sources
→ Data Quality & Point-in-Time Layer
→ Quant Engine
→ Stock Valuation / PUT / CALL / Portfolio Engines
→ Opportunity Ranker
→ Local Obsidian RAG
→ LLM Gate
→ Investment Committee / Analyst LLM
→ Risk Validation
→ Structured Decision
→ SQLite/Parquet + Obsidian Memory

LangGraph is the orchestration/state-machine layer. It does not imply that every node must be an LLM agent.

## 3. Component responsibilities

### Data Engine
Provides market prices, B3 stocks, options chains, fundamentals, corporate actions/dividends, implied volatility, Greeks, open interest, volume/liquidity, macro and permitted news/sentiment data.

### Point-in-Time Layer
Prevents look-ahead bias and data leakage. Historical decisions must use information actually available at the decision timestamp.

### Quant Engine
Computes indicators, statistics, liquidity filters, scoring, risk metrics and other deterministic analytics.

### Stock Valuation Engine
Produces valuation ranges and scenarios (Bear/Base/Bull), fair-value ranges, accumulation zones, reduce zones and sell zones. A single fair value is not treated as ground truth.

### PUT Opportunity Engine
Evaluates cash-secured PUT opportunities using strike, premium, effective acquisition price, liquidity, IV, Greeks, event risk, distance to valuation and margin of safety.

### Covered CALL Engine
Evaluates covered CALL opportunities using strike, premium, IV, Greeks, liquidity, potential stock appreciation, total return if exercised and opportunity cost.

### Portfolio Context Engine
Evaluates holdings, average cost, weights, concentration, cash, open PUT/CALL obligations, potential assignment capital and portfolio-level risk.

### Opportunity Ranker
Compares alternative actions: BUY/ACCUMULATE, SELL PUT, HOLD/WAIT, SELL CALL, REDUCE and SELL. It must consider opportunity cost rather than optimizing each instrument independently.

### Obsidian / RAG
Human-editable semantic memory containing investment policy, theses, valuation assumptions, strategy rules, research and investment lessons. Retrieval is selective; the complete vault is never sent to an LLM by default.

### LLM Gate
Determines whether an LLM call is materially justified. No LLM call is required merely because a pipeline run occurred.

### Investment Committee / Analyst LLM
Provides reasoning, synthesis, contradiction analysis and qualitative judgment only after deterministic evidence has been prepared.

### Risk Validation
Checks decision consistency against hard risk rules, portfolio constraints and strategy policy before a decision is persisted.

### Decision / Memory
Every decision must be structured and auditable and may include action, confidence, thesis, evidence, risks, opportunity cost, invalidation conditions, timestamp, model, prompt version and cost metadata.

## 4. LangGraph approved flow

`load_snapshot → validate_data → compute_quant → value_stock → analyze_options → load_portfolio → rank_opportunities → retrieve_memory → llm_gate → investment_committee → risk_validation → persist_decision → update_memory`

Nodes may be deterministic, retrieval-based or LLM-based. The LLM Gate controls expensive reasoning stages.

## 5. Investment decision space

The system must support at minimum:

- BUY / ACCUMULATE
- HOLD
- WAIT
- SELL PUT
- SELL COVERED CALL
- REDUCE
- SELL
- AVOID

For options, the decision unit is instrument + underlying + position/context + strike + expiration + premium + relevant option metrics.

## 6. Change control

Every change is classified:

- **C1 — Correction:** typo, documentation or non-functional correction.
- **C2 — Implementation:** implementation of already-approved design.
- **C3 — Configuration:** model, threshold, parameter or environment configuration.
- **C4 — Internal component:** change inside a component without changing its public responsibility.
- **C5 — Interface:** change to a contract, schema or dependency between components.
- **C6 — Flow/LangGraph:** change to orchestration, state or node sequencing.
- **C7 — Architecture:** change to component boundaries, responsibilities, data flow or fundamental design principles.

### Mandatory impact review

Before implementing C4–C7 changes, answer:

1. Does component responsibility change?
2. Does LangGraph flow/state change?
3. Does any interface or schema change?
4. Is a new data source introduced?
5. Is a new LLM call introduced?
6. Can look-ahead bias or data leakage be introduced?
7. Can an investment decision regress?

C7 changes require an ADR. C5/C6 changes require explicit interface/flow review. Decision-changing changes require regression tests and golden cases.

## 7. Non-negotiable engineering rules

1. No LLM for deterministic mathematics when reliable code can perform it.
2. No whole-Obsidian-vault prompt by default.
3. No live execution in the initial implementation.
4. No historical backtest using future information.
5. No architecture changes hidden inside implementation work.
6. Prompts are versioned because prompts are part of the system behavior.
7. Model changes are configuration changes but require benchmark validation.
8. Investment-policy changes in Obsidian must be traceable and reviewable.
9. Every phase ends with **Implement → Test → Validate → Freeze → Next phase**.
10. Ideas for later phases are recorded but not implemented early.

## 8. Roadmap baseline

0. BASELINE
1. ENVIRONMENT
2. DATA
3. QUANT
4. VALUATION
5. OPTIONS
6. PORTFOLIO
7. OPPORTUNITY RANKER
8. OBSIDIAN/RAG
9. LLM GATE
10. INVESTMENT COMMITTEE
11. RISK
12. DECISION
13. MEMORY
14. BACKTEST
15. WALK-FORWARD
16. PAPER
17. LIVE COPILOT
18. EXECUTION — FUTURE

The order is normative unless changed through governance.
