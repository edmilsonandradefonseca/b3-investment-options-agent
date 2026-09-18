# B3 Investment & Options Agent
# Use Cases — Investment Options V1.1
# Conversational Investment Copilot Extension

**Version:** 1.1  
**Status:** PROPOSED  
**Date:** 2026-09-16  
**Baseline:** `USE_CASES_INVESTMENT_OPTIONS_V1.md`  
**Related:** `ARCHITECTURE_V3.1.md`, `PHASE7_KICKOFF_2026-09-15(1).md`

---

## 1. Purpose

This document extends the existing investment and options use cases with a conversational access layer inside the Dashboard.

The new capability is:

> **UC-01 — Conversational Investment Copilot**

The Copilot allows the investor to ask questions in natural language and receive a response grounded in the same deterministic portfolio, market, options, valuation and opportunity intelligence already used by the system.

This is an interface extension, not a second investment-intelligence architecture.

---

## 2. Architectural Principle

The Dashboard Copilot is a client of the existing B3 Orchestrator.

It must not implement investment calculations, opportunity ranking, portfolio analysis or independent decision logic.

```text
Dashboard / Copilot
        |
        v
B3 Orchestrator Server
        |
        v
b3_orchestrator()
        |
        v
LangGraph
        |
        +--> deterministic portfolio / market / options context
        |
        +--> specialist agents
        |
        +--> synthesis
        |
        +--> reasoning
        |
        +--> risk validation
        |
        v
Structured response
        |
        v
Dashboard / Copilot
```

The same intelligence workflow must serve the Dashboard, ChatGPT and future clients.

---

# 3. UC-01 — Conversational Investment Copilot

## 3.1 Objective

Allow the investor to ask an investment question in natural language and obtain a contextualized response based on:

- current portfolio;
- available/committed capital;
- market information;
- options information;
- valuation;
- deterministic OpportunitySet;
- portfolio concentration;
- existing positions;
- opportunity cost;
- retrieved evidence;
- specialist analyses;
- synthesis;
- reasoning;
- risk validation.

The response remains decision support. The human remains the final decision authority.

---

## 3.2 Primary Example

### User

> Tenho R$ 80 mil disponíveis. Existe alguma boa oportunidade?

### Expected processing

```text
1. Interpret user intent
2. Identify available capital = R$ 80,000
3. Obtain deterministic OpportunitySet
4. Consider capital requirements
5. Consider current portfolio context
6. Consider valuation / return / risk / concentration
7. Run relevant specialist analyses
8. Synthesize specialist outputs
9. Produce DecisionProposal
10. Run Risk Validation
11. Return structured explanation to the user
```

The question must not be sent directly to the LLM as an unrestricted investment prompt.

The deterministic system must establish the factual opportunity universe first.

---

## 3.3 Expected Response Content

Where available, the Copilot response should expose:

- question understood;
- available capital;
- relevant opportunities;
- action associated with each opportunity;
- capital requirement;
- deterministic ranking/priority;
- valuation information;
- return information;
- relevant risks;
- portfolio impact;
- concentration impact;
- opportunity cost;
- specialist synthesis;
- material uncertainties;
- evidence references;
- source references;
- `as_of`;
- data-quality status;
- risk-validation status;
- human-review requirement.

The presentation may be conversational, but the underlying facts must remain structured and auditable.

---

# 4. Conversational Use-Case Families

## 4.1 Capital

Examples:

- "Tenho R$ 80 mil disponíveis. Existe alguma boa oportunidade?"
- "Quais oportunidades cabem em R$ 50 mil?"
- "Quanto capital preciso para essa PUT?"
- "Quanto capital ficaria comprometido?"
- "Existe alguma oportunidade que use menos capital?"

The capital constraint is an input/context condition. It must not cause the LLM to invent or recalculate opportunity economics.

---

## 4.2 Portfolio

Examples:

- "Como está minha carteira?"
- "Onde estou mais concentrado?"
- "Quais posições têm maior exposição?"
- "Tenho alguma posição que merece revisão?"
- "Como uma nova oportunidade afetaria minha carteira?"

Portfolio facts come from the deterministic Portfolio Intelligence layer.

---

## 4.3 Opportunities

Examples:

- "Quais oportunidades existem agora?"
- "Existe alguma oportunidade em PETR4?"
- "Quais oportunidades estão disponíveis para minha carteira?"
- "Existe uma oportunidade melhor do que uma posição que já tenho?"

The OpportunitySet remains the authoritative deterministic opportunity universe.

---

## 4.4 Valuation

Examples:

- "PETR4 está barata?"
- "Qual o preço de acumulação?"
- "Qual é o valuation base?"
- "Qual oportunidade tem valuation mais favorável?"

The Copilot explains valuation results produced by deterministic valuation engines.

It must not silently recalculate valuation in the LLM.

---

## 4.5 Positions and Options

Examples:

- "Como está minha PUT?"
- "Minha CALL está coberta?"
- "Quanto capital está comprometido?"
- "Devo analisar o fechamento dessa opção?"
- "Existe uma alternativa de ROLL?"
- "Existe uma oportunidade melhor do que manter essa posição?"

These questions use existing position, option and lifecycle intelligence.

---

## 4.6 Comparison

Examples:

- "É melhor comprar PETR4 ou vender uma PUT?"
- "Compare essa oportunidade com minha posição atual."
- "Existe uma alternativa melhor para esse capital?"
- "Qual o custo de oportunidade de manter essa posição?"

Comparison must use deterministic comparison data where available and preserve the provenance of the compared facts.

---

# 5. UC-01 Processing Contract

The Copilot follows the following logical contract:

```text
USER QUESTION
      |
      v
OrchestratorRequest
      |
      v
Intent / Context Interpretation
      |
      v
Deterministic Context
      |
      +--> PortfolioContext
      +--> PortfolioIntelligence
      +--> Market Analysis
      +--> Options Analysis
      +--> Valuation
      +--> OpportunitySet
      +--> Action Candidates
      |
      v
Specialist Agents
      |
      v
Synthesis
      |
      v
Decision Reasoning
      |
      v
Risk Validation
      |
      v
OrchestratorResponse
```

The Copilot does not bypass the orchestrator.

---

# 6. LLM Boundary for UC-01

The LLM may:

- interpret the user's natural-language question;
- explain deterministic results;
- synthesize specialist analyses;
- reconcile conflicting evidence;
- formulate a thesis;
- identify uncertainty;
- identify unanswered questions;
- explain portfolio implications;
- prepare human-review material.

The LLM may not:

- invent market data;
- invent portfolio data;
- invent opportunities;
- change deterministic ranking;
- silently recalculate valuation;
- override portfolio constraints;
- bypass Risk Validation;
- execute orders;
- place orders;
- make the final investment decision.

---

# 7. Golden Conversational Cases

## GC-C01 — Available Capital Opportunity Discovery

**Input**

> Tenho R$ 80 mil disponíveis. Existe alguma boa oportunidade?

**Required behavior**

The system must identify the capital constraint and evaluate the deterministic OpportunitySet against the user's available capital and portfolio context.

The response must preserve:

- deterministic opportunity identity;
- capital requirements;
- ranking/priority produced upstream;
- relevant valuation;
- relevant risk;
- portfolio impact;
- evidence/provenance;
- `as_of`;
- data quality;
- risk-validation result.

**Negative requirements**

The system must not:

- invent an opportunity;
- create a new ranking inside the LLM;
- alter deterministic calculations;
- issue an executable order.

---

## GC-C02 — Capital Insufficient

**Input**

> Tenho R$ 20 mil. Essa PUT cabe na minha carteira?

**Required behavior**

The response must use the deterministic capital requirement and portfolio context and clearly identify whether the capital constraint is satisfied.

---

## GC-C03 — Portfolio-Aware Opportunity

**Input**

> Tenho essa carteira. Existe alguma oportunidade que melhore minha diversificação?

**Required behavior**

The system must consider existing portfolio exposure and deterministic opportunity information before producing qualitative reasoning.

---

## GC-C04 — Existing Position vs New Opportunity

**Input**

> Vale a pena analisar uma nova oportunidade em vez de manter essa posição?

**Required behavior**

The system must use the existing position context, relative opportunity information and opportunity-cost information when available.

---

## GC-C05 — BUY vs SELL PUT

**Input**

> É melhor comprar PETR4 ou vender uma PUT de PETR4?

**Required behavior**

The response must compare the two deterministic opportunity paths and explain the differences using the existing evidence and portfolio context.

---

## GC-C06 — Valuation Question

**Input**

> PETR4 está barata?

**Required behavior**

The response must use the available deterministic valuation result, explain the relevant assumptions and distinguish valuation facts from qualitative reasoning.

---

## GC-C07 — Existing Option Position

**Input**

> Como está minha PUT e existe alguma alternativa que eu deveria analisar?

**Required behavior**

The system must combine position intelligence, option analysis, available opportunities and qualitative reasoning without executing or recommending an automatic trade.

---

## GC-C08 — Insufficient Evidence

**Input**

> Qual a melhor coisa para eu fazer agora?

**Required behavior**

If the available deterministic context or evidence is insufficient, the system must not invent a conclusion.

It should identify what is known, what is missing and whether additional analysis is required.

---

# 8. Dashboard Surface

The Dashboard should expose the Copilot as one of the primary human-facing surfaces:

```text
DASHBOARD
|
+-- Overview
+-- Portfolio
+-- Opportunities
+-- Valuation
+-- Options
+-- Copilot
```

The Copilot is a presentation/client layer.

It does not become a producer of intelligence.

---

# 9. Relationship to Existing Use Cases

UC-01 does not replace existing investment and options use cases.

It provides a conversational entry point to them.

```text
Existing Use Cases
       |
       v
Deterministic / Agent Intelligence
       |
       v
B3 Orchestrator
       |
       +--------------------+
       |                    |
       v                    v
Dashboard screens        Copilot
```

This prevents duplication of investment logic between traditional Dashboard views and conversational interaction.

---

# 10. Governance and Auditability

Every substantive Copilot answer should remain traceable through:

```text
User Question
    ->
Intent / Context
    ->
Source Data
    ->
Deterministic Analysis
    ->
Opportunity / Portfolio Context
    ->
Specialist Analysis
    ->
Synthesis
    ->
Decision Proposal
    ->
Risk Validation
    ->
Response
```

The conversational response must not become an opaque replacement for the underlying structured decision-support record.

---

# 11. MVP Scope

### Included

- Dashboard Copilot UI;
- natural-language question submission;
- `OrchestratorRequest` integration;
- reuse of `b3_orchestrator()`;
- reuse of existing LangGraph workflow;
- deterministic portfolio/opportunity context;
- specialist agents;
- synthesis;
- reasoning;
- Risk Validation;
- structured/auditable response;
- Golden Conversational Cases.

### Not included

- autonomous trading;
- order execution;
- automatic portfolio changes;
- unrestricted agent loops;
- independent Copilot ranking;
- independent Copilot valuation engine;
- unrestricted web browsing as a decision source.

---

# 12. Acceptance Criteria

UC-01 is accepted when:

1. A user can submit a natural-language investment question from the Dashboard.
2. The Dashboard sends the request through the B3 Orchestrator.
3. The same `b3_orchestrator()` workflow used by other clients is reused.
4. Deterministic portfolio/opportunity information is established before LLM reasoning.
5. Specialist analyses remain separate from deterministic facts.
6. Synthesis does not replace deterministic facts.
7. Reasoning does not invent missing data.
8. Risk Validation remains downstream of the proposal.
9. No execution path exists.
10. The response exposes provenance and `as_of` where applicable.
11. GC-C01 through GC-C08 are covered by tests or explicit staged implementation.
12. The Dashboard contains no duplicated investment-calculation logic.

---

# 13. Architectural Decision

**Decision:** APPROVED FOR MVP DESIGN

The Conversational Investment Copilot is a **new client/interface capability over the existing B3 Investment Intelligence workflow**, not a new intelligence engine.

The central architectural invariant remains:

```text
Server      -> controls access
LangGraph   -> controls workflow
Agents      -> analyze domains
Engines     -> calculate
MCP         -> controlled tools/connectors
Knowledge   -> context and memory
LLM         -> reasoning and synthesis
Risk        -> validates
Human       -> decides
```

The Copilot therefore extends the system without changing the fundamental V3.1 separation of responsibilities.
