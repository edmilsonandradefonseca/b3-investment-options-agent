# ADR 0001 — Initial Architecture Baseline

- **Status:** Accepted
- **Date:** 2026-09-13
- **Decision type:** C7 — Architecture

## Context

The project is intended to support long-term investment decisions in B3 stocks and options. The goal is decision support, not autonomous trading. The system must control LLM cost, preserve auditability, support quantitative analysis and maintain a durable human-editable investment memory.

## Decision

Adopt a hybrid architecture with the following principles:

1. Python-first for deterministic calculations and analytics.
2. Local-first for data processing, retrieval and persistent structured state where practical.
3. LLM-for-reasoning for qualitative synthesis, contradiction analysis and judgment where materially useful.
4. Obsidian as the human-editable semantic knowledge layer.
5. SQLite/Parquet as structured state and analytical data stores.
6. LangGraph as workflow/state orchestration rather than as a requirement to make every node an LLM agent.
7. An explicit LLM Gate before expensive reasoning stages.
8. Point-in-time data as a hard requirement for historical decisions and backtests.
9. No live trading execution during the initial roadmap.

## Consequences

This architecture deliberately differs from a generic multi-agent LLM trading framework. It reduces unnecessary LLM calls, makes quantitative calculations reproducible, and keeps investment policy and memory under human control.

The architecture can later add optional multi-agent debate or execution capabilities only through formal change control and validation.

## Rejected alternatives

- LLM-heavy agent for every analytical function.
- Sending the entire Obsidian vault to every model call.
- Autonomous live trading as an initial feature.
- Treating a single model fair value as deterministic truth.

## Validation requirement

Future architectural changes must pass the impact review defined in `docs/ARCHITECTURE.md` and, when decision-changing, include regression tests and golden cases.
