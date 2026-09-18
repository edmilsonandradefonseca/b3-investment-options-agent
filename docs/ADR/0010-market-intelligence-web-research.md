# ADR 0010 — Market Intelligence Agent with Web Research

## Status

Accepted — MVP implementation.

## Context

The B3 agent needs current information that can materially affect investments, not only information about individual stocks. The existing specialist `MarketAnalysisAgent` interprets supplied deterministic facts but does not perform live research.

The new Market Intelligence Agent therefore owns the web-research responsibility for current market context while deterministic providers remain authoritative for structured market and portfolio facts.

## Scope

Research may include, when relevant to the requested instrument, portfolio or sector:

- company and corporate events;
- Brazilian and global inflation;
- interest rates and central-bank decisions;
- fiscal and economic policy;
- USD/BRL and other major currencies;
- commodities and global supply chains;
- global rates, liquidity and risk appetite;
- China and other major economies;
- wars, geopolitical conflicts and sanctions;
- climate, weather and natural-disaster events;
- regulation and economically relevant policy events;
- capital flows and foreign investment;
- sector developments, earnings, M&A and investment announcements.

The agent must establish a causal or contextual link before treating a broad event as relevant to an investment.

## Boundary

`BTG`, `BRAPI` and `OpLab` remain the source of truth for structured portfolio, stock and option data. The Market Intelligence Agent does not recalculate those values, replace deterministic analytics, rank opportunities, execute orders, or make the final investment decision.

The agent uses the OpenAI Responses API hosted `web_search` tool for live public-web research and returns structured evidence with URL, publication time when available, retrieval time, publisher, topic, relevance and affected tickers.

## Point-in-Time

The requested `as_of` timestamp is part of the agent contract. Research instructions require information to have been available by that timestamp. Evidence with ambiguous timing should not be treated as historical fact.

## Output

`MarketInsight` contains:

- summary and findings;
- macro factors;
- geopolitical factors;
- climate factors;
- sector factors;
- risks and uncertainties;
- auditable web evidence;
- source references.

This output is intended to feed RAG/Knowledge Graph and downstream investment agents. It is not itself a final decision.

## Architecture

```text
BTG + BRAPI + OpLab
        |
        v
Deterministic Context
        |
        +----------------------+
        |                      |
        v                      v
 Market Intelligence      Deterministic Analysis
        |
        | live web search
        v
 MarketInsight + Evidence
        |
        v
 RAG / Knowledge Graph
        |
        v
 Investment Reasoning -> Risk -> Human
```

## Non-goals

- autonomous trading or order execution;
- replacing deterministic calculations with an LLM;
- treating a single news article as unquestioned truth;
- building a separate generic NewsFeed provider.
