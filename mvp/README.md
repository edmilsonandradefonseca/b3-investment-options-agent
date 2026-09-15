# B3 AI Investment Copilot — MVP

This directory defines the product/demo layer of the B3 Investment Options Agent.

The MVP exposes the same deterministic domain intelligence through two interfaces:

- **Dashboard** — human-facing portfolio and opportunity analysis.
- **MCP** — read-only interface for AI agents such as Gemini/Antigravity.

The MVP does not execute trades. Investment calculations and ranking remain in the B3 domain layer under `src/b3_agent/`.

## Target architecture

```text
                         B3 AI INVESTMENT COPILOT
                                      |
                    +-----------------+-----------------+
                    |                                   |
              Web Dashboard                         MCP Server
               Human UI                          AI Agent Interface
                    |                                   |
                    +-----------------+-----------------+
                                      |
                               B3 Agent Core
                                      |
              +---------------------+---------------------+
              |                     |                     |
        Portfolio             Valuation             Opportunity
       Intelligence                                Intelligence
              |                     |                     |
              +---------------------+---------------------+
                                      |
                                  BTG Excel
```

## MVP scope

1. Load the real BTG `Renda Variavel` workbook through the existing deterministic ingestion pipeline.
2. Present portfolio and options intelligence in an interactive dashboard.
3. Present ranked opportunities using the explicit Phase 7 ranking policy.
4. Expose read-only capabilities through MCP.
5. Demonstrate the same domain facts through Dashboard and MCP.
6. Validate Gemini/Antigravity → MCP → B3 Agent → structured result as a separate integration gate.

## Explicitly out of scope

- trade/order execution
- autonomous investment decisions
- LLM-based ranking
- hidden scoring weights
- machine learning optimization
- paper trading
- embeddings/RAG as a decision engine

## Implementation status

- Real BTG Excel → `PortfolioContext`: **validated**
- `PortfolioContext` → `PortfolioIntelligenceEngine`: **validated**
- MCP STDIO discovery/invocation: **validated locally**
- Dashboard: **next implementation step**
- Gemini/Antigravity E2E: **next integration gate**
