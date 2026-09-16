# Agents V0.1

## Scope

Agent V0.1 adds three specialist reasoning agents without moving deterministic business logic into the LLM layer.

## Agents

- `MarketAnalysisAgent`: interprets market analysis, signals and threats.
- `PortfolioAnalysisAgent`: interprets portfolio context, risk analysis and action candidates.
- `OptionsAnalysisAgent`: interprets options analysis, opportunities and action candidates.
- `InvestmentReasoningAgent`: synthesizes specialist/context/evidence into `DecisionProposal`.
- `RiskValidator`: deterministic final gate.

## Boundary

Provider adapters, analytical engines and opportunity ranking remain upstream. Specialist agents may interpret supplied facts but must not fetch data, recalculate metrics, rerank opportunities, mutate state, or execute orders.

## LangGraph

`retrieve -> deterministic_context -> market_analysis -> portfolio_analysis -> options_analysis -> reason -> validate`.

The current implementation is intentionally sequential. Parallel specialist execution can be introduced later without changing the specialist contracts.

## RAG

`ObsidianRetriever` remains the retrieval component. Evidence is passed through `AgentContext`/`SpecialistContext` with source references.

## V0.1 non-goals

- no order execution
- no autonomous trading
- no provider access from agents
- no replacement of deterministic analytical engines
- no semantic/vector RAG requirement yet
