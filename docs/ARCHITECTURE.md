# Architecture — B3 Investment & Options Agent

## 1. Purpose and architectural principle

The B3 Investment & Options Agent is a postgraduate research project at PUC-Rio exploring an enterprise-oriented Agentic AI architecture for context-aware investment decision support.

The approved principle is:

> **Deterministic first, knowledge/context aware, LLM-for-reasoning, risk-validated.**

Deterministic computation must not be delegated to an LLM when reliable code can perform it. LLM calls are controlled by explicit gates and operate on prepared context.

## 2. High-level architecture

```text
                 Dashboard
                     │
                     ▼
               Orchestrator
                     │
                     ▼
                 LangGraph
                     │
       ┌─────────────┼─────────────┐
       ▼             ▼             ▼
 Deterministic   Knowledge      Agents
    Engine        Context
       │             │             │
 Quant/Valuation  Qdrant/KG     Reasoning
 Options/Portfolio Obsidian     Synthesis
       │             │             │
       └─────────────┼─────────────┘
                     ▼
                    Risk
                     │
                     ▼
                  Decision
```

The architecture separates four concerns:

1. **Deterministic computation** — numerical analytics, valuation, options and portfolio intelligence.
2. **Knowledge and context** — structured evidence, semantic knowledge and relationship-oriented context.
3. **Agentic reasoning** — specialized analysis, synthesis and controlled LLM reasoning.
4. **Governance and validation** — risk rules, provenance, point-in-time correctness and auditable decisions.

## 3. Current implementation status

The current repository contains implemented components for:

- market-data provider adapters;
- point-in-time and data-quality contracts;
- quantitative analysis;
- stock valuation;
- PUT/CALL analysis;
- portfolio capital/risk and portfolio intelligence;
- opportunity intelligence;
- MCP portfolio context;
- LangGraph workflow orchestration;
- Qdrant vector-store foundation and retrieval contracts;
- Knowledge Graph contracts and in-memory implementation;
- Obsidian integration;
- LLM Gate and model abstraction;
- automated tests and CI;
- Streamlit MVP and a React/Tauri desktop frontend foundation.

### Important implementation boundary

**Qdrant is implemented as a local vector-store foundation.** Production semantic embeddings, hybrid retrieval, reranking and broader retrieval optimization remain research/MVP work.

**Knowledge Graph support currently provides backend-neutral contracts and an in-memory implementation.** A concrete Neo4j persistence adapter is a subsequent implementation step; the architecture must not imply that Neo4j persistence is already operational.

This distinction between implemented, foundation and planned capabilities is part of the project's research transparency.

## 4. LangGraph orchestration

The orchestration layer models the workflow as explicit state transitions rather than assuming every node is an LLM agent.

Conceptually:

```text
Data / Snapshot
      │
      ▼
Data Quality & PIT
      │
      ▼
Deterministic Context
      │
      ├──────────────┐
      ▼              ▼
Knowledge        Specialist
Context            Agents
      │              │
      └──────┬───────┘
             ▼
          Synthesis
             │
             ▼
        LLM Reasoning
             │
             ▼
       Risk Validation
             │
             ▼
          Decision
             │
             ▼
        Persistence
```

The implemented workflow includes retrieval, deterministic context preparation, knowledge context, specialist analysis, synthesis/reasoning, validation and optional persistence.

## 5. Deterministic engines

Deterministic engines remain the numerical source of truth.

### Quantitative analysis

Computes indicators, statistics, liquidity filters, scoring and risk metrics.

### Valuation

Produces valuation scenarios and ranges rather than treating a single fair value as ground truth.

### Options

Evaluates PUT and covered CALL opportunities using strike, premium, effective acquisition/exercise economics, liquidity, IV, Greeks, event risk and portfolio context.

### Portfolio intelligence

Combines holdings, average cost, weights, cash, option obligations, assignment capital and portfolio-level risk.

## 6. Knowledge Context

Knowledge is treated as a first-class architectural layer.

The target context model combines:

```text
Structured Facts
      +
Semantic Evidence
      +
Relationships
      +
Prior Decisions / Memory
      +
Point-in-Time Metadata
      │
      ▼
Knowledge Context
```

The design goal is to give agents the **right context**, not the maximum amount of context.

Key requirements:

- provenance;
- temporal validity;
- source attribution;
- relevance;
- confidence;
- lifecycle/version metadata;
- controlled context size.

## 7. Agentic AI

The project explores reusable agent patterns rather than a single monolithic prompt.

Agents may specialize in:

- market analysis;
- portfolio analysis;
- options analysis;
- synthesis;
- risk-oriented validation.

The orchestrator determines when components execute and what context they receive.

The LLM is used for reasoning, synthesis and qualitative interpretation after deterministic evidence is prepared.

## 8. MCP boundary

MCP provides a controlled interface for exposing selected application capabilities to external agents.

Current principles:

- read-only boundary;
- explicit contracts;
- no fabricated portfolio data;
- no broker execution;
- deterministic calculations remain in the B3 domain layer;
- invalid or missing source data fails explicitly.

## 9. Risk, governance and auditability

Risk validation occurs after reasoning and before a decision is persisted.

A structured decision should be traceable to:

- source data;
- retrieved knowledge/context;
- deterministic calculations;
- strategy/policy context;
- reasoning/model metadata;
- validation results;
- timestamp;
- applicable prompt/version metadata where relevant.

The architecture explicitly avoids autonomous execution in the initial scope.

## 10. Data and privacy

No API credentials belong in the repository.

Personal portfolio/account information remains local and outside the public repository.

Historical analysis must respect point-in-time correctness and avoid look-ahead bias.

## 11. Change control

Changes are classified as:

- **C1 — Correction**
- **C2 — Implementation**
- **C3 — Configuration**
- **C4 — Internal component**
- **C5 — Interface**
- **C6 — Flow/LangGraph**
- **C7 — Architecture**

C7 changes require an ADR. C5/C6 changes require explicit interface/flow review. Decision-changing changes require regression tests and golden cases.

Before C4–C7 changes, review:

1. component responsibility;
2. LangGraph flow/state;
3. interfaces/schemas;
4. data sources;
5. LLM calls;
6. look-ahead/data leakage risk;
7. decision regression risk.

## 12. Engineering rules

1. No LLM for deterministic mathematics when reliable code can perform it.
2. No whole-Obsidian-vault prompt by default.
3. No live execution in the initial implementation.
4. No historical backtest using future information.
5. No hidden architecture changes inside implementation work.
6. Prompts are versioned because prompts are part of system behavior.
7. Model changes require benchmark validation.
8. Investment-policy changes must be traceable and reviewable.
9. Every material phase follows **Implement → Test → Validate → Freeze → Next phase**.
10. Experimental capabilities must be clearly separated from production-ready capabilities.

## 13. Next architectural evolution

The next MVP evolution should focus on:

1. completing the end-to-end dashboard experience;
2. integrating Qdrant retrieval into the Knowledge Context path;
3. implementing and evaluating production embedding/retrieval strategies;
4. adding a concrete Neo4j adapter when the graph use cases justify persistence;
5. strengthening agent evaluation and feedback loops;
6. adding end-to-end observability;
7. measuring context quality, reuse, latency, cost and decision traceability.

The architecture should evolve through measured use cases rather than adding infrastructure without a demonstrated need.
