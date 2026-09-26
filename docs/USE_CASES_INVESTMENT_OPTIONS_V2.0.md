# B3 Investment & Options Agent
# Use Cases — Investment Intelligence V2.0
# Continuous Learning & Experience Intelligence Baseline

**Version:** 2.0  
**Status:** APPROVED FUNCTIONAL BASELINE  
**Date:** 2026-09-26  
**Supersedes for forward design:** `USE_CASES_INVESTMENT_OPTIONS_V1.1.md`  
**Architecture baseline:** V3.1 remains the current frozen implementation architecture until a new architecture revision is formally approved.

---

## 1. Purpose

This document defines the approved business/use-case baseline that will drive the next architecture revision of the B3 Investment & Options Agent.

The architecture must be derived from these use cases, not the other way around.

The central product vision is:

> The B3 Agent must combine deterministic market/portfolio/options analytics with persistent experience, contextual research and continuous learning so that future analyses reuse what the system has already observed and validated.

The system remains a decision-support platform. The human remains the final decision authority.

---

## 2. Core principles derived from the use cases

1. **Deterministic facts remain authoritative.**
2. **Point-in-time correctness is mandatory.**
3. **Past operations are treated as experience, not merely as ledger records.**
4. **Learning must be persistent and reusable across future analyses.**
5. **Recent evidence may receive greater weight, but historical evidence must not be silently deleted.**
6. **Market regime and contextual similarity matter in addition to simple recency.**
7. **Correlation/association must not be presented as causation without appropriate evidence.**
8. **Insights and learnings must preserve provenance, confidence and contradictions.**
9. **LLMs interpret and synthesize; statistical and deterministic engines validate measurable claims.**
10. **Dashboard/Copilot present intelligence; they do not duplicate business logic.**
11. **No autonomous order execution is part of this scope.**
12. **The system should avoid reinventing the same analysis when validated prior learning already exists.**

---

# 3. Approved Use Cases

## UC-01 — Portfolio Intelligence

### Objective

Provide a current, deterministic and contextual view of the portfolio.

### Questions

- Como está minha carteira?
- Onde estou mais concentrado?
- Quais posições têm maior exposição?
- Quanto capital está disponível, comprometido ou potencialmente comprometido?
- Quais posições merecem revisão?
- Como uma nova operação alteraria concentração, risco ou liquidez?

### Required intelligence

- positions;
- average cost;
- current price;
- market value;
- cash;
- committed/assignment capital;
- concentration;
- sector/issuer exposure;
- option obligations;
- realized/unrealized P&L;
- portfolio-level risk.

### Output

Structured portfolio intelligence with provenance, `as_of`, quality status and risk context.

---

## UC-02 — Options Position & Lifecycle Intelligence

### Objective

Understand the current state, economics and lifecycle of each option position.

### Questions

- Como está minha PUT/CALL?
- Qual o P&L?
- Quanto capital está comprometido?
- Qual o risco de exercício?
- Minha CALL está coberta?
- Existe alternativa de fechamento ou roll?
- O prêmio ainda compensa o risco?
- Existe uma oportunidade melhor do que manter a posição?

### Required intelligence

- option type;
- underlying;
- strike;
- expiration;
- DTE;
- premium;
- market price;
- IV;
- Greeks where available;
- moneyness;
- assignment/exercise exposure;
- covered/uncovered state;
- realized/unrealized P&L;
- alternative structures.

---

## UC-03 — Opportunity Discovery

### Objective

Identify opportunities worth investigating given current market conditions, portfolio constraints and available capital.

### Questions

- Quais oportunidades existem agora?
- Existe alguma oportunidade em PETR4?
- Tenho R$ 50 mil; quais oportunidades cabem nesse capital?
- Existe uma oportunidade melhor do que manter uma posição atual?
- Quais oportunidades melhoram diversificação sem elevar demais o risco?

### Required intelligence

- deterministic opportunity universe;
- valuation;
- market state;
- option state;
- capital requirement;
- portfolio impact;
- risk;
- liquidity;
- prior experience;
- opportunity cost.

### Rule

The LLM must not invent an opportunity outside the canonical analytical pipeline.

---

## UC-04 — Strategy Comparison & What-if

### Objective

Compare alternative actions and scenarios using the same deterministic facts and explicit assumptions.

### Questions

- Comprar PETR4 ou vender uma PUT?
- Manter a posição ou fechar?
- Fazer roll ou esperar?
- Comprar ação, vender CALL coberta ou manter caixa?
- Qual o custo de oportunidade entre duas estratégias?

### Required intelligence

- expected capital usage;
- payoff;
- valuation;
- historical outcomes;
- scenario assumptions;
- risk;
- portfolio impact;
- liquidity;
- opportunity cost.

### Output

A structured comparison that separates deterministic facts, historical evidence, assumptions and qualitative reasoning.

---

## UC-05 — Market & Regime Intelligence

### Objective

Describe the current market regime and provide context for portfolio, option and opportunity analysis.

### Example context

- IBOV level/trend;
- realized volatility;
- drawdown;
- breadth;
- foreign investor flow;
- USD/BRL;
- SELIC;
- DI curve;
- commodities;
- sector conditions;
- market/stock/option volatility;
- relevant events.

### Questions

- O mercado está lateral, em tendência ou em stress?
- A volatilidade atual está alta ou baixa em relação ao histórico?
- O fluxo estrangeiro está favorecendo ou pressionando o mercado?
- O regime atual é parecido com algum regime histórico importante?

### Architectural consequence

`MarketRegime` should become an explicit analytical/context object in the next architecture revision.

---

## UC-06 — Contextual Factor Intelligence

### Objective

Discover, test and explain which factors are associated with the behavior of an asset, strategy or historical operation.

### Candidate factors

- IBOV;
- foreign investor flow;
- interest rates / DI / SELIC;
- USD/BRL;
- realized volatility;
- implied volatility;
- momentum;
- liquidity;
- sector variables;
- commodity prices;
- company events;
- macro events;
- news/sentiment;
- portfolio state.

### Examples

For PETR4:

- Brent;
- USD/BRL;
- dividend events;
- oil-sector news;
- foreign flow;
- IBOV;
- volatility.

For VALE3:

- iron ore;
- China indicators/events;
- USD/BRL;
- foreign flow;
- IBOV;
- volatility.

### Rule

The agent may propose relationships, but measurable relationships must be evaluated by statistical/deterministic methods before being promoted to a validated learning.

---

## UC-07 — Historical Operation Reconstruction

### Objective

Reconstruct the information environment that existed when an operation was opened, managed and closed.

### Required reconstruction

```text
OPERATION
  +
FEATURE SNAPSHOT AT ENTRY
  +
FEATURE SNAPSHOT DURING POSITION
  +
FEATURE SNAPSHOT AT EXIT
  +
OUTCOME
```

### Entry snapshot may include

- underlying price;
- returns;
- realized volatility;
- option IV/Greeks;
- strike distance;
- DTE;
- premium;
- IBOV state;
- foreign flow;
- rates;
- FX;
- commodities;
- news/events;
- portfolio context.

### Outcome may include

- realized P&L;
- return;
- holding period;
- maximum adverse excursion;
- maximum favorable excursion;
- assignment/exercise;
- exit reason.

### Rule

All features must respect point-in-time availability. Future information must never leak into the historical reconstruction.

---

## UC-08 — Experience & Continuous Learning

### Objective

Transform real operations and their outcomes into reusable, persistent experience.

### Core question

> O que minhas operações anteriores ensinaram ao sistema e esse aprendizado continua válido?

### Learning example

```text
Strategy: SHORT PUT PETR4
Conditions:
- IBOV sideways
- foreign flow positive
- IV/RV > threshold
- strike distance within a range
- DTE within a range

Observed:
- N operations
- wins/losses
- expected return
- dispersion
- adverse/favorable excursion

Learning:
historically favorable association under these conditions
```

### Learning lifecycle

```text
CANDIDATE
   ↓
VALIDATING
   ↓
ACTIVE
   ↓
STRENGTHENING / WEAKENING
   ↓
DRIFT_DETECTED / UNDER_REVIEW
   ↓
SUPERSEDED / ARCHIVED
```

### Required properties

- sample size;
- supporting evidence;
- contradicting evidence;
- effect size where applicable;
- confidence;
- market regime;
- valid period;
- last confirmed timestamp;
- recency/aging metadata;
- provenance;
- version/model information.

### Rule

Old learnings are not silently deleted. They can be weakened, contradicted or superseded.

---

## UC-09 — Historical Similarity & Precedent Retrieval

### Objective

Find previous market/portfolio/strategy states similar to the current state and analyze what happened afterward.

### Questions

- Já vimos algo parecido?
- Quais operações ocorreram em contextos similares?
- Qual foi o resultado?
- Quais diferenças atuais tornam o precedente menos comparável?
- Existe um learning anterior para este regime?

### Relevance should consider

- feature similarity;
- market regime similarity;
- semantic relevance;
- time/recency;
- evidence quality;
- sample confidence.

### Important rule

Recency is important but must not be the only criterion. An older observation from a highly similar regime may be more relevant than a newer observation from a different regime.

---

## UC-10 — Research, News & Event Intelligence

### Objective

Turn external information into structured evidence that can confirm, contradict or update existing theses and learnings.

### Flow

```text
NEW INFORMATION
      ↓
Entity/Event extraction
      ↓
Relationship/context lookup
      ↓
Affected assets / positions / theses / learnings
      ↓
Evidence assessment
      ↓
Confirm / contradict / update / no material impact
```

### Questions

- O que mudou desde a última análise?
- Essa notícia afeta alguma posição?
- Essa notícia confirma ou contradiz uma tese?
- Esse evento altera um learning existente?
- Existe nova evidência para um fator já monitorado?

### Rule

News summaries alone are not learning. Learning requires evidence/context and appropriate validation.

---

## UC-11 — Risk, Scenario & Stress Intelligence

### Objective

Quantify what can happen to the portfolio and option positions under adverse or alternative scenarios.

### Examples

- IBOV -10%;
- PETR4 -15%;
- USD/BRL +8%;
- Brent -15%;
- iron ore -20%;
- IV +40%;
- DI curve +100 bps.

### Required outputs

- portfolio P&L impact;
- option exposure;
- assignment/exercise exposure;
- capital requirement;
- concentration;
- liquidity implications;
- key sensitivities;
- risk-validation status.

### Principle

Historical learning complements but does not replace stress analysis. The future may differ from historical regimes.

---

## UC-12 — Decision Rationale & Conversational Copilot

### Objective

Provide a natural-language interface over the complete B3 intelligence workflow.

### Questions

- Por que você está dizendo isso?
- Quais operações sustentam esse learning?
- O que mudou desde ontem?
- Quais fatores favorecem e contradizem essa oportunidade?
- Qual o nível de confiança?
- Quais riscos podem invalidar a tese?
- Que informação ainda falta?

### Expected rationale

A response may expose:

- current market regime;
- deterministic facts;
- portfolio context;
- option context;
- relevant historical precedents;
- active learnings;
- recent vs long-term evidence;
- supporting factors;
- contradicting factors;
- uncertainties;
- risk;
- provenance;
- `as_of`;
- human-review requirement.

### Architectural role

The Copilot is a client/presentation surface. It does not own independent investment logic.

---

# 4. Continuous Learning Invariant

The next architecture revision must support two mandatory hooks:

```text
PRE-ANALYSIS
→ retrieve relevant prior experience / learnings

POST-OUTCOME
→ evaluate result
→ update statistics
→ confirm / weaken / contradict / supersede learnings
→ persist new knowledge
```

A post-analysis insight may become a learning candidate, but outcome-dependent learning must only be finalized when the relevant outcome is known.

---

# 5. Temporal / Aging Requirement

Financial relationships are non-stationary.

The system must therefore preserve full historical evidence while also supporting:

- rolling/sliding statistics;
- recent windows;
- exponential or configurable temporal decay;
- market-regime similarity;
- drift detection;
- confidence update;
- learning versioning.

Conceptually:

```text
Historical relevance
=
recency
× regime similarity
× feature similarity
× evidence quality
× sample confidence
```

The exact formula and weights are implementation/calibration decisions, not part of this use-case freeze.

---

# 6. Memory Requirements Derived from the Use Cases

The use cases imply three complementary runtime persistence domains.

## Structured / analytical memory

Target:

```text
SQLite / Parquet
```

Stores:

- transactions;
- market data;
- portfolio data;
- option data;
- feature snapshots;
- outcomes;
- statistics;
- regime history;
- audit/provenance.

## Semantic memory

Target:

```text
Qdrant
```

Stores/retrieves semantic representations of:

- learnings;
- insights;
- theses;
- research;
- event evidence;
- prior analyses;
- historical rationale.

Qdrant is a retrieval system, not the numerical source of truth.

## Relational memory / Knowledge Graph

Target:

```text
Neo4j
```

Represents reusable relationships such as:

```text
PETR4 → exposed_to → BRENT
VALE3 → exposed_to → IRON_ORE
Option → underlying → Stock
Learning → applies_to → Strategy
Learning → valid_in → MarketRegime
Learning → supported_by → Operation
Learning → contradicted_by → Evidence
Learning → supersedes → Learning
```

Relationships must support temporal validity where relevant.

## Human-readable presentation

Human-readable theses, decisions, learnings, rationale and research summaries are rendered by Dashboard/Copilot from the three canonical runtime memory domains.

Obsidian is not a required runtime memory backend in the V4.0 direction. Project architecture and session documentation remain in Git/GitHub.

---

# 7. Dashboard Implications

The Dashboard should evolve beyond current positions/opportunities views and eventually expose:

```text
Overview
Portfolio
Options
Opportunities
Market Regime
Experience & Learning
Historical Similarity
Research / Events
Risk / Stress
Copilot
```

A future **Experience & Learning Intelligence** view should be able to show:

- learning status;
- confidence;
- age;
- last confirmation;
- sample size;
- long-term performance;
- recent-window performance;
- supporting factors;
- contradicting factors;
- drift status;
- source operations/evidence;
- rationale.

The Dashboard remains a presentation surface and must not implement the learning/statistical logic itself.

---

# 8. Use Case → Architecture Traceability Gate

Before approving the next architecture revision, each approved use case must be mapped to:

```text
USE CASE
   ↓
required data
   ↓
required deterministic/statistical engine
   ↓
required agent(s)
   ↓
memory read/write requirements
   ↓
workflow
   ↓
architecture component
   ↓
tests / acceptance criteria
```

Each required capability will be classified as:

- `EXISTS`
- `PARTIAL`
- `MISSING`

This traceability matrix is the next architecture-gate artifact.

---

# 9. Relationship to V1.1

V1.1 introduced the Conversational Investment Copilot.

V2.0 changes the framing:

> The Copilot is no longer the primary use case. It is the conversational interface over the full investment-intelligence and continuous-learning platform.

The approved functional focus becomes:

```text
Portfolio
+
Options
+
Market
+
Opportunity
+
Experience
+
Learning
+
Research
+
Risk
        ↓
Decision Support / Copilot
```

V1.1 remains useful as historical documentation of the Copilot MVP design.

---

# 10. Governance

These use cases are approved as the functional baseline for architecture review.

They do not themselves authorize implementation changes.

Because the resulting architecture is expected to alter knowledge, learning, persistence and LangGraph responsibilities, the next architecture revision is a **C7 architecture change** and must follow the project governance process:

```text
Approved Use Cases
      ↓
Traceability Matrix
      ↓
Architecture Gate
      ↓
ADR(s)
      ↓
New Architecture Revision
      ↓
Contracts
      ↓
Implementation Plan
      ↓
Implementation / Tests / Validation / Freeze
```

Existing deterministic engines, point-in-time semantics, Risk Validation and human-decision boundaries must be preserved unless explicitly changed and approved.

---

# 11. Approved Functional Baseline

The approved set is:

1. **UC-01 — Portfolio Intelligence**
2. **UC-02 — Options Position & Lifecycle Intelligence**
3. **UC-03 — Opportunity Discovery**
4. **UC-04 — Strategy Comparison & What-if**
5. **UC-05 — Market & Regime Intelligence**
6. **UC-06 — Contextual Factor Intelligence**
7. **UC-07 — Historical Operation Reconstruction**
8. **UC-08 — Experience & Continuous Learning**
9. **UC-09 — Historical Similarity & Precedent Retrieval**
10. **UC-10 — Research, News & Event Intelligence**
11. **UC-11 — Risk, Scenario & Stress Intelligence**
12. **UC-12 — Decision Rationale & Conversational Copilot**

---

# 12. Next Step

Create the **Use Case → Architecture Traceability Matrix** and review every current B3 component against these twelve approved use cases before defining the next architecture version.
