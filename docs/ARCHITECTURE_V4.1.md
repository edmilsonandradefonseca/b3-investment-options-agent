# B3 Investment & Options Agent — Architecture V4.1

**Version:** 4.1  
**Status:** PROPOSED ADDITIVE EXTENSION  
**Date:** 2026-09-28  
**Base architecture:** V4.0 APPROVED / FROZEN  
**Scope:** Fast Router + Local Background Reasoning + Senior LLM Escalation  
**Compatibility rule:** V4.1 does not reopen or replace the deterministic/statistical V4.0 baseline.

---

## 1. Purpose

Architecture V4.1 adds a lightweight AI execution-routing layer to the B3 Investment & Options Agent in order to:

- reduce unnecessary remote LLM usage;
- exploit the local DeepSeek R1 8B for asynchronous reasoning work;
- preserve deterministic numerical authority;
- keep interactive latency low;
- escalate ambiguity and high-value reasoning to OpenClaw / ChatGPT Luna;
- prepare richer context before senior-LLM analysis;
- preserve all V4.0 safety, provenance, point-in-time and human-decision invariants.

The architectural intent is not to make the B3 Agent more autonomous in financial decision making. It is to make the intelligence pipeline more efficient.

---

## 2. Non-negotiable V4 invariants

V4.1 preserves:

1. Deterministic/statistical services own measurable facts.
2. SQLite/Parquet remain canonical structured truth.
3. Qdrant and Neo4j remain retrieval/relationship projections, not numerical authority.
4. LLMs may interpret, synthesize and explain but may not override canonical facts.
5. Opportunities must originate from the canonical analytical pipeline.
6. Historical reconstruction must remain point-in-time safe.
7. Statistical association must not be promoted to causality by an LLM.
8. No autonomous B3 order execution.
9. Human remains final investment decision authority.
10. Architecture V4.0 business logic remains frozen.

---

## 3. V4.1 architectural pattern

```text
                         INPUT / TASK
                              |
                              v
                   +----------------------+
                   | FAST ROUTER V1       |
                   | deterministic code   |
                   +----------+-----------+
                              |
          +-------------------+-------------------+
          |                   |                   |
          v                   v                   v
  DETERMINISTIC PATH     BACKGROUND PATH     AMBIGUOUS / COMPLEX
  BRAPI / OPLAB / BCB    DeepSeek R1 8B      OpenClaw / Luna
  Python / SQL / engines asynchronous         senior reasoning
          |                   |                   |
          +-------------------+-------------------+
                              |
                              v
                     STRUCTURED RESULT
                              |
                              v
              SQLite / Qdrant / Neo4j
                              |
                              v
                     Copilot / React UI
```

The Fast Router is not an LLM.

DeepSeek R1 8B is not the Fast Router.

Luna/OpenClaw is not used for tasks that are already deterministically resolvable.

---

## 4. Fast Router V1

### 4.1 Role

Fast Router V1 is a small deterministic code component responsible only for routing.

It must not:
- perform investment reasoning;
- generate investment recommendations;
- calculate portfolio facts;
- infer market facts;
- execute external actions;
- directly alter learning state.

It decides only which execution path receives a task.

### 4.2 Design principle

```text
KNOWN CONTRACT     -> deterministic route
KNOWN BACKGROUND   -> background queue/job
KNOWN COMPLEX      -> OpenClaw/Luna
AMBIGUOUS          -> OpenClaw/Luna
```

No small LLM is required in V4.1.

### 4.3 Router inputs

The router should use metadata before natural-language heuristics:

- namespace: `b3`;
- source: API / React / scheduler / CLI / João integration / Copilot;
- explicit job type;
- explicit endpoint;
- extracted ticker when trivial;
- explicit operation identifier;
- explicit use-case hint when already known;
- free-text user request.

### 4.4 Router output contract

Example:

```json
{
  "namespace": "b3",
  "intent": "market_price_lookup",
  "use_case": "UC-01",
  "execution_mode": "sync",
  "route": "deterministic",
  "target": "market_provider",
  "match": "MATCH_STRONG",
  "matched_rule": "B3_MARKET_PRICE_V1"
}
```

Ambiguous request:

```json
{
  "namespace": "b3",
  "intent": null,
  "use_case": null,
  "execution_mode": "sync",
  "route": "senior_llm",
  "target": "openclaw",
  "match": "AMBIGUOUS",
  "matched_rule": null
}
```

Background request:

```json
{
  "namespace": "b3",
  "intent": "nightly_ticker_intelligence",
  "use_case": "UC-10",
  "execution_mode": "background",
  "route": "local_reasoning",
  "target": "deepseek-r1:8b",
  "match": "MATCH_EXACT",
  "matched_rule": "B3_NIGHTLY_RESEARCH_V1"
}
```

### 4.5 Match classes

Only three operational classes are required:

- `MATCH_EXACT`
- `MATCH_STRONG`
- `AMBIGUOUS`

If ambiguous, route upward. The router must fail safe rather than guess.

### 4.6 First deterministic rules

Examples:

| Request / source | Route |
|---|---|
| price/quote for known ticker | market provider |
| portfolio snapshot | portfolio engine |
| option Greeks / DTE / moneyness | options engine |
| stress scenario with explicit parameters | UC-11 deterministic pipeline |
| scheduled macro refresh | macro job |
| scheduled nightly research intelligence | DeepSeek background |
| compare two investment strategies | OpenClaw/Luna |
| vague thesis question | OpenClaw/Luna |
| unknown intent | OpenClaw/Luna |

---

## 5. DeepSeek R1 8B role

### 5.1 Positioning

DeepSeek R1 8B is a **Background Reasoning Worker**.

It is intentionally excluded from the synchronous critical path because local CPU tests showed high reasoning latency even for trivial prompts.

Its strengths are exploited where latency is secondary and local compute can replace repeated remote inference.

### 5.2 Allowed responsibilities

DeepSeek may:

- summarize large research/news batches;
- deduplicate semantically similar narratives after deterministic retrieval;
- extract entities, events, arguments and contradictions;
- create per-ticker research digests;
- identify possible thesis changes for review;
- generate supporting/contradicting evidence summaries;
- synthesize deterministic portfolio/options outputs into narrative context;
- identify items that deserve escalation;
- prepare candidate questions for senior analysis;
- summarize historical precedents already retrieved by canonical services;
- draft learning candidates for later validation;
- prepare overnight intelligence dossiers.

### 5.3 Prohibited responsibilities

DeepSeek must not:

- create authoritative prices or Greeks;
- alter canonical P&L;
- create opportunities outside UC-03 canonical pipeline;
- promote unvalidated causal claims;
- directly change deterministic ranking;
- directly promote a learning to validated/active state;
- place trades;
- choose financial actions autonomously;
- overwrite canonical facts.

### 5.4 Structured output contract

DeepSeek outputs should be schema-constrained.

Example:

```json
{
  "ticker": "PETR4",
  "as_of": "2026-09-28T22:30:00-03:00",
  "summary": "...",
  "material_change": true,
  "events": [],
  "supporting_evidence_refs": [],
  "contradicting_evidence_refs": [],
  "risks": [],
  "catalysts": [],
  "thesis_change_candidate": true,
  "escalation_required": true,
  "escalation_reason": "material new evidence",
  "model": "deepseek-r1:8b"
}
```

Every output must preserve provenance references from the deterministic/research inputs.

---

## 6. Luna / OpenClaw role

OpenClaw / ChatGPT Luna acts as **Senior Reasoning and Ambiguity Resolution**.

It receives:

- ambiguous interactive tasks;
- complex multi-use-case questions;
- strategy comparisons requiring synthesis;
- escalated DeepSeek dossiers;
- cases with conflicting evidence;
- high-value opportunity reviews;
- final conversational explanations.

Luna/OpenClaw does not become numerical authority.

The preferred flow is:

```text
canonical facts
+ retrieved evidence
+ prior learnings
+ DeepSeek background synthesis when available
        |
        v
OpenClaw / Luna
        |
        v
final analysis / explanation for human decision
```

---

## 7. B3 nightly intelligence pipeline

### 7.1 Objective

Use idle/off-peak local CPU to precompute research and context for portfolio and candidate assets.

### 7.2 Proposed sequence

```text
22:00 market / portfolio / macro refresh
22:05 options refresh
22:10 news / research ingestion
22:20 deterministic features / regime / factors
22:30 DeepSeek per-ticker analysis
23:00 DeepSeek portfolio synthesis
23:15 options narrative review
23:30 opportunity/watchlist enrichment
23:45 consolidated Daily Intelligence
00:00 persistence + escalation queue
```

Exact timing is configurable and not part of the architecture invariant.

### 7.3 Initial pilot

The first implementation target should be **UC-10 Research, News & Event Intelligence**.

Pilot:

```text
portfolio + watchlist
    -> research/news last window
    -> deterministic retrieval/dedup/preprocess
    -> DeepSeek structured analysis
    -> material-change detection
    -> persistence
    -> optional Luna escalation
```

---

## 8. Use-case mapping

| UC | DeepSeek role | Luna/OpenClaw role | Deterministic authority |
|---|---|---|---|
| UC-01 Portfolio | narrative/change synthesis | complex portfolio interpretation | portfolio services |
| UC-02 Options | narrative risk review | strategy discussion | options engines |
| UC-03 Opportunity | enrich canonical candidates | deep opportunity analysis | opportunity pipeline |
| UC-04 What-if | prepare pros/cons from facts | final synthesis | scenario/payoff engines |
| UC-05 Regime | interpret regime output | cross-domain reasoning | regime engine |
| UC-06 Factors | explain tested factors | higher-level synthesis | statistical engine |
| UC-07 History | reconstruct narrative | precedent interpretation | PIT reconstruction |
| UC-08 Learning | draft learning candidate | explain implications | learning validation |
| UC-09 Similarity | summarize retrieved precedents | nuanced comparison | retrieval/similarity engine |
| UC-10 Research | primary background use | material escalations | research/evidence pipeline |
| UC-11 Stress | explain results | strategic implications | stress engine |
| UC-12 Copilot | precomputed context | primary conversational reasoning | CopilotContext facts |

---

## 9. Persistence

V4.1 introduces no new canonical database authority.

Existing domains remain:

- SQLite / Parquet: structured truth;
- Qdrant: semantic retrieval;
- Neo4j: relationship context.

DeepSeek outputs are derived artifacts and must be stored as derived intelligence with:

- source refs;
- `as_of`;
- model/version;
- prompt/template version;
- creation timestamp;
- quality/status;
- escalation status.

They must be rebuildable.

---

## 10. Resource and scheduling policy

The local model runs on CPU and must remain subordinate to operational services.

Recommended controls:

- background execution only;
- sequential or tightly bounded concurrency;
- `Nice=10` or lower CPU priority;
- optional systemd `CPUWeight`;
- bounded context/batch sizes;
- timeout;
- retry policy;
- dedup key;
- no uncontrolled fan-out.

The B3 runtime, shared embedding, João services and canonical data refreshes take priority.

---

## 11. Implementation compatibility assessment

### Existing integration points

V4.1 fits existing B3 code with limited changes because the repository already contains:

- `src/b3_agent/jobs/` for scheduled/background work;
- systemd timer installation pattern in `scripts/install_macro_refresh_timer.sh`;
- `src/b3_agent/llm/client.py` as an LLM abstraction point;
- `CopilotContextBuilder` as the deterministic conversational boundary;
- existing deterministic UC-01..UC-12 services;
- shared Qdrant/Neo4j runtime already validated.

### Minimal implementation additions

Expected new components:

```text
src/b3_agent/routing/
    models.py
    rules.py
    router.py

src/b3_agent/llm/
    ollama_client.py

src/b3_agent/jobs/
    nightly_intelligence.py

scripts/
    install_nightly_intelligence_timer.sh
```

Optional later:

```text
src/b3_agent/intelligence/
    local_reasoning_store.py
    escalation_queue.py
```

No rewrite of portfolio, options, market regime, factors, learning, historical reconstruction or stress engines is required.

### Complexity assessment

- Core architecture change: LOW.
- Domain-engine change: NONE expected.
- Persistence schema change: LOW / optional.
- Runtime integration: LOW-MEDIUM.
- Testing/calibration: MEDIUM.
- Operational risk: controllable because background reasoning is non-authoritative and can be disabled without impairing canonical B3 functionality.

---

## 12. Failure behavior

If Ollama/DeepSeek is unavailable:

- deterministic B3 continues;
- nightly local synthesis is marked unavailable/failed;
- no canonical fact is lost;
- senior LLM can still operate from deterministic context;
- retry may occur later.

If OpenClaw/Luna is unavailable:

- deterministic and DeepSeek background processing continue;
- escalations remain pending;
- no API fallback should occur unless explicitly configured by policy.

---

## 13. Observability

Record:

- router rule hit;
- ambiguous fallback count;
- route target;
- route latency;
- DeepSeek queue depth;
- execution duration;
- token/eval counts when available;
- CPU/RAM impact;
- schema-validation failures;
- escalations generated;
- escalations consumed;
- derived-intelligence freshness.

These metrics will determine whether future router rules should be expanded.

---

## 14. Migration plan

### Phase A — Router contract
1. Implement deterministic Router V1.
2. Add route logging.
3. Unknown/ambiguous -> OpenClaw.
4. Do not add a small local classifier.

### Phase B — DeepSeek pilot
1. Add Ollama client.
2. Implement UC-10 nightly research job.
3. Enforce structured JSON schema.
4. Store derived output with provenance.
5. Benchmark CPU/RAM/runtime.

### Phase C — escalation
1. Add escalation status/queue.
2. Feed material cases to OpenClaw/Luna.
3. Measure reduction in remote context volume.

### Phase D — expand only after validation
Potential expansion:
- UC-05/06;
- UC-01/02;
- UC-03 opportunity enrichment;
- UC-08 learning candidate synthesis.

---

## 15. V4.1 decision

B3 V4.1 adopts:

- **Fast Router = deterministic code only**;
- **ambiguity = OpenClaw / Luna**;
- **DeepSeek R1 8B = asynchronous background reasoning worker**;
- **deterministic engines = canonical authority**;
- **OpenClaw/Luna = senior reasoning layer**;
- **no small LLM router in V4.1**.

This is an additive runtime/intelligence extension and does not reopen the frozen V4.0 domain architecture.
