# B3 Investment & Options Agent — Architecture V4.3

**Version:** 4.3  
**Status:** IMPLEMENTED / RUNTIME VALIDATED  
**Date:** 2026-09-30  
**Base:** V4.0 + V4.1 + V4.2  
**Scope:** redefine the local DeepSeek role as asynchronous Evidence pre-analysis and enrichment.

---

## 1. Executive decision

V4.3 keeps DeepSeek R1 8B in the B3 architecture, but removes it from any mandatory senior-reasoning chain.

The new role is:

> **DeepSeek is a local asynchronous Evidence Analyst.**

It runs in background over already validated canonical Evidence and produces rebuildable derived dossiers.

It is **not**:

- a router;
- a source of truth;
- a materiality authority;
- a numerical authority;
- a required hop before OpenClaw/Luna;
- a blocker for interactive analysis;
- a mandatory producer of user-facing answers.

OpenClaw/Luna remains the senior reasoning path for ambiguous, complex or interactive questions and must be able to operate directly from canonical B3 facts and Evidence whether or not a DeepSeek dossier exists.

---

## 2. Why V4.3 changes the DeepSeek role

V4.2 production acceptance proved that the local model can run correctly, but also exposed the limits of putting it inline before senior reasoning.

In the real PETR4 replay:

- the canonical Evidence bundle was small;
- local DeepSeek reasoning consumed roughly three minutes;
- the model reached its configured output ceiling;
- its dossier was incomplete;
- it introduced an unsupported share-class description;
- OpenClaw/Luna correctly fell back to the canonical Evidence and preserved the Evidence limitation.

Therefore the strongest demonstrated value of DeepSeek is not “mandatory reasoning before Luna”.

Its most useful economic role is to spend otherwise idle local compute to prepare context ahead of time so that future interactive/senior analysis can reuse it without waiting for it.

---

## 3. Preserved invariants

V4.3 does not reopen V4.0–V4.2 authority decisions.

Still authoritative:

- deterministic/statistical services for prices, portfolio, options, P&L, risk and measurable facts;
- SQLite/Parquet for canonical structured truth;
- canonical Evidence for observed external facts;
- deterministic materiality before any LLM;
- PIT semantics and append-only Evidence history;
- Fast Router as deterministic routing;
- Qdrant/Neo4j as projections;
- OpenClaw/Luna as senior reasoning;
- human as final investment authority;
- no autonomous trading.

DeepSeek output is always **derived intelligence**.

---

## 4. V4.3 high-level architecture

```text
                    REACT / API / SCHEDULER / COPILOT
                                   |
                                   v
                         DETERMINISTIC FAST ROUTER
                                   |
          +------------------------+------------------------+
          |                        |                        |
          v                        v                        v
  DETERMINISTIC FACTS       BACKGROUND EVIDENCE       COMPLEX / AMBIGUOUS
  portfolio/options/etc.         PIPELINE                   |
          |                        |                        |
          |                        v                        |
          |                CANONICAL EVIDENCE               |
          |                        |                        |
          |                        v                        |
          |              LOCAL ANALYSIS QUEUE               |
          |                        |                        |
          |                        v                        |
          |                 DEEPSEEK R1 8B                  |
          |               async local analyst               |
          |                        |                        |
          |                        v                        |
          |               DERIVED LOCAL DOSSIER             |
          |                        |                        |
          |                  quality gate                    |
          |                        |                        |
          +------------------------+------------------------+
                                   |
                                   v
                         SENIOR CONTEXT BUILDER
                          canonical first
                                   |
                 +-----------------+-----------------+
                 |                                   |
                 v                                   v
       dossier ready + valid                dossier absent/stale/invalid
                 |                                   |
                 +-----------------+-----------------+
                                   |
                                   v
                           OPENCLAW / LUNA
                           senior reasoning
                                   |
                                   v
                              HUMAN / UI
```

Critical property:

> **OpenClaw/Luna never waits for DeepSeek.**

---

## 5. DeepSeek V4.3 responsibilities

### 5.1 Allowed

DeepSeek may asynchronously:

- summarize multiple already-retrieved Evidence records;
- identify repeated narratives across sources;
- identify contradictions between Evidence records;
- extract candidate risks and catalysts for later review;
- produce per-ticker overnight Evidence digests;
- produce sector/theme digests from canonical Evidence;
- prepare questions that a senior analyst should investigate;
- flag that senior review may be useful;
- summarize historical precedents already retrieved by canonical services;
- enrich derived RAG context;
- precompute background context for UC-10 and future Copilot sessions.

### 5.2 Prohibited

DeepSeek must not:

- decide deterministic materiality;
- create or correct canonical Evidence;
- infer authoritative issuer/security identity;
- invent prices, returns, Greeks, P&L or probabilities;
- alter portfolio/accounting truth;
- change deterministic opportunity ranking;
- create a trade recommendation as an authoritative output;
- autonomously trigger an order;
- become the only reason for senior escalation;
- block OpenClaw/Luna while local analysis is pending;
- have its claims written back into canonical Evidence.

---

## 6. Asynchronous local-analysis lifecycle

The local analysis lifecycle is explicitly separated from evidence ingestion.

```text
CANONICAL EVIDENCE
      |
      v
deterministic eligibility policy
      |
      +--> not eligible -> SKIPPED
      |
      v
ENQUEUE
      |
      v
PENDING
      |
      v
RUNNING
      |
      +--> local/runtime failure -> FAILED
      |
      v
COMPLETED
      |
      v
QUALITY GATE
      |
      +--> output limit hit / invalid refs / stale -> DEGRADED
      |
      +--> valid -> READY
```

The queue must be idempotent by an Evidence fingerprint.

Reprocessing is required when:

- the Evidence set changes;
- the prompt/policy version changes;
- the local model contract changes materially;
- the dossier becomes stale under retention policy.

---

## 7. Local Evidence Dossier contract

A local dossier is rebuildable derived intelligence.

Minimum metadata:

```json
{
  "analysis_id": "...",
  "ticker": "PETR4",
  "evidence_fingerprint": "...",
  "evidence_refs": ["..."],
  "created_at": "...",
  "model": "deepseek-r1:8b",
  "prompt_version": "b3_local_evidence_analyst_v2",
  "status": "READY",
  "quality_flags": [],
  "analysis": "...",
  "thinking_chars": 0,
  "input_chars": 0,
  "eval_count": 0,
  "num_predict": 768
}
```

The dossier does not become an Evidence object.

It may reference Evidence, but Evidence must never reference the dossier as its factual source.

---

## 8. Eligibility policy

DeepSeek should consume local CPU only when a background dossier has plausible reuse value.

Initial V4.3 eligibility:

- Evidence conclusion is `MATERIAL_FOUND`; and
- at least one canonical material Evidence/event exists; and
- an identical Evidence fingerprint has not already produced a current dossier.

Do not enqueue:

- `NO_MATERIAL_FOUND`;
- `COVERAGE_INSUFFICIENT`;
- deterministic price/portfolio/options calculations;
- trivial interactive lookups;
- an unchanged Evidence bundle already analyzed.

Candidates may be added later under a separate policy version.

---

## 9. Senior reasoning policy

Senior reasoning is independent of local-analysis availability.

### Interactive complex request

```text
user question
   |
   v
Fast Router -> OpenClaw/Luna
   |
   +--> canonical facts
   +--> canonical Evidence
   +--> latest READY local dossier, if exact Evidence fingerprint matches
```

If the dossier is:

- pending;
- missing;
- stale;
- failed;
- truncated;
- inconsistent with the current Evidence fingerprint;

then it is omitted.

Senior reasoning proceeds immediately.

### Scheduled background research

DeepSeek may finish a dossier without invoking Luna.

A dossier may create a **senior-review candidate**, but senior invocation is controlled by deterministic policy or explicit human/user demand.

---

## 10. Quality gate for local dossiers

A DeepSeek dossier is eligible for senior context only if all are true:

1. model call completed;
2. content is non-empty;
3. Evidence fingerprint matches the current canonical bundle;
4. every Evidence/source reference belongs to the allowed input set;
5. output did not hit the configured generation ceiling;
6. dossier is not stale;
7. no runtime failure flag exists.

Initial quality flags:

```text
OUTPUT_LIMIT_REACHED
MISSING_CONTENT
STALE_EVIDENCE
UNKNOWN_EVIDENCE_REF
MODEL_FAILURE
RUNTIME_FAILURE
```

A degraded dossier may be persisted for diagnostics but must not be injected into senior context.

---

## 11. Evidence fingerprint

The fingerprint must be deterministic and independent of DeepSeek.

Recommended input:

- ticker;
- sorted Evidence IDs/source refs;
- materiality state;
- relevant Evidence content hashes;
- local-analysis policy version.

This gives:

- idempotent queueing;
- stale-dossier detection;
- exact provenance matching;
- safe reuse.

---

## 12. Persistence layout

Initial filesystem implementation:

```text
data/derived/local_evidence_analyst/
    queue/
        <analysis_id>.json
    runs/
        <analysis_id>.json
    latest/
        PETR4.json
    manifests/
        latest.json
```

Later migration to SQLite is allowed without changing the contract.

All artifacts are derived and rebuildable.

---

## 13. Resource policy

The local model remains background-only.

Required controls:

- one local reasoning job at a time per host;
- low CPU priority;
- bounded context;
- bounded output;
- bounded batch count;
- no uncontrolled fan-out;
- model unload after inference unless a bounded batch is intentionally in progress;
- B3 deterministic services take priority;
- João and B3 must eventually share a host-level reasoning lock/semaphore.

A busy local model may delay DeepSeek analysis.

It must never delay deterministic B3 APIs or senior interactive reasoning.

---

## 14. Use-case role in V4.3

| Use case | DeepSeek local analyst | OpenClaw/Luna |
|---|---|---|
| UC-01 Portfolio | optional overnight narrative enrichment | complex interpretation |
| UC-02 Options | optional background risk digest | strategy discussion |
| UC-03 Opportunity | enrich already-canonical candidates | deep candidate review |
| UC-04 What-if | no critical role | interactive synthesis |
| UC-05 Regime | optional narrative enrichment | cross-domain reasoning |
| UC-06 Factors | optional explanation cache | nuanced interpretation |
| UC-07 History | background precedent digest | precedent reasoning |
| UC-08 Learning | draft-only candidate context | human-facing implications |
| UC-09 Similarity | summarize retrieved precedents | comparison |
| UC-10 Research | **primary DeepSeek use case** | senior review only when needed |
| UC-11 Stress | optional explanation cache | strategic implications |
| UC-12 Copilot | precomputed optional context | **primary conversational reasoning** |

---

## 15. Router change

V4.3 preserves the deterministic Fast Router.

Scheduled UC-10 research continues to route to a background target, but the semantic target changes from:

```text
"run DeepSeek inline"
```

to:

```text
"prepare/enqueue local Evidence analysis"
```

Complex or ambiguous user requests continue directly to OpenClaw/Luna.

No LLM is introduced into routing.

---

## 16. V4.2 compatibility

V4.3 supersedes only the mandatory shape implied by V4.2 section 27:

```text
Canonical Evidence -> DeepSeek -> escalation -> Luna
```

with:

```text
Canonical Evidence -------------------------------> Luna
       |
       +--> async DeepSeek dossier --optional----> Luna context
```

All V4.2 acquisition, Evidence, PIT, issuer mapping, materiality and coverage rules remain unchanged.

Gate A/B/C/D history remains valid as evidence that the components work; V4.3 changes orchestration, not the factual authority model.

---

## 17. Implementation components

V4.3 introduces:

```text
src/b3_agent/intelligence/local_evidence_analysis.py
    LocalEvidenceAnalysisRequest
    LocalEvidenceDossier
    LocalEvidenceQueue
    LocalEvidenceAnalyst
    LocalEvidenceContextSelector

src/b3_agent/jobs/local_evidence_analyst.py
    LocalEvidenceAnalystJob

scripts/run_local_evidence_analyst.py
```

Nightly UC-10 becomes:

```text
retrieve + normalize + materiality
        |
        +--> persist canonical/research result
        |
        +--> enqueue local-analysis request
```

The separate worker consumes the queue.

---

## 18. V4.3 acceptance criteria

V4.3 implementation is acceptable when:

- V4.0–V4.2 regression tests remain green;
- material Evidence can be queued idempotently;
- no-material and coverage-gap states do not enqueue;
- worker processes queued Evidence in background;
- local dossier is stored separately from canonical Evidence;
- output-limit detection marks the dossier degraded;
- unknown Evidence refs prevent dossier reuse;
- senior context selection never waits for DeepSeek;
- missing/pending/failed/degraded dossier returns canonical Evidence context immediately;
- exact-current READY dossier can be added as optional secondary context;
- Fast Router remains deterministic;
- OpenClaw/Luna remains independently callable from canonical Evidence;
- local analysis remains bounded and background-only.

---

## 19. Migration rule

Do not delete the existing V4.2 acceptance replay.

It remains a component validation tool.

Production orchestration should migrate toward the V4.3 async local-analysis contract.

---

## 20. V4.3 frozen decision

The architectural decision introduced by V4.3 is:

> **DeepSeek R1 8B is retained as an asynchronous local Evidence Analyst whose output is optional derived context. OpenClaw/Luna senior reasoning must never depend on DeepSeek availability or completion.**

This change is motivated by observed production behavior and preserves all deterministic, Evidence, PIT, no-autonomous-trading and human-authority invariants.


---

## 21. As-built runtime validation — 2026-09-30

V4.3 was validated on the production Ubuntu host with real PETR4 CVM Evidence.

The staged acceptance proved:

- canonical Evidence acquisition/materiality completed before local reasoning;
- enqueue returned in approximately 2.6 seconds;
- DeepSeek was not invoked inline;
- the separate local worker consumed the queued request;
- DeepSeek produced a degraded dossier after reaching the 768-token ceiling;
- the quality gate marked it `DEGRADED` with `INVALID_JSON` and `OUTPUT_LIMIT_REACHED`;
- the senior context builder omitted the degraded dossier;
- canonical Evidence remained available to the senior path;
- all three runtime stages returned zero;
- final marker: `V4_3_ACCEPTANCE=PASS`.

This negative-path validation is intentional evidence for the V4.3 architecture: local-model quality failure does not block or contaminate senior reasoning.

V4.3 is therefore implemented and runtime validated.

Repository merge/freeze sequencing remains separate because V4.3 is stacked on the V4.2 branch, whose CVM RAD live Gate D depends on external credentials.
