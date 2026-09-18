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

Deterministic analyses and specialist outputs have separate state keys. In particular, `market_analysis` and `options_analysis` remain upstream-owned deterministic inputs; LLM outputs are stored as `market_agent_analysis`, `portfolio_agent_analysis` and `options_agent_analysis`. This prevents an agent interpretation from replacing the facts it was asked to interpret.

## LangGraph

`retrieve -> deterministic_context -> {market_analysis, portfolio_analysis, options_analysis} -> reason -> validate`.

The three specialist nodes form an independent fan-out from the deterministic context and join at `reason`. This allows parallel execution while keeping synthesis downstream of all specialist results.

## RAG

`ObsidianRetriever` remains the retrieval component. Evidence is passed through `AgentContext`/`SpecialistContext` with source references.

## V0.1 non-goals

- no order execution
- no autonomous trading
- no provider access from agents
- no replacement of deterministic analytical engines
- no semantic/vector RAG requirement yet
