# B3 Investment & Options Agent

Personal investment decision-support system for the Brazilian stock market (B3).

## Purpose

The project is designed as an investment copilot, not an autonomous trading system. Its core decisions are based on valuation, portfolio context, quantitative analysis and options overlays:

- BUY / ACCUMULATE
- HOLD / WAIT
- REDUCE / SELL
- SELL CASH-SECURED PUT
- SELL COVERED CALL

## Architectural principle

**Python-first, local-first, LLM-for-reasoning.**

Deterministic calculations, data processing, valuation, option analytics, scoring, risk checks and backtesting are implemented outside the LLM. LLM calls are selective and justified by an explicit LLM Gate.

Obsidian is the human-editable semantic knowledge layer. SQLite/Parquet are used for structured state and historical analytical data. LangGraph orchestrates the workflow and state transitions.

## Governance

The architecture is governed by `docs/ARCHITECTURE.md` and changes follow the change-control rules documented there. Architectural decisions are recorded in `docs/ADR/` and material changes are recorded in `docs/CHANGELOG.md`.

## Implementation roadmap

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

Each phase follows: **Implement → Test → Validate → Freeze → Next phase.**

## Status

Repository initialized. Governance baseline is being established before implementation begins.
