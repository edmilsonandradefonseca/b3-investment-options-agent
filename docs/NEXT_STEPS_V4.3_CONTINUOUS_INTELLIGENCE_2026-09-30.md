# V4.3 Continuous Intelligence — Next Steps — 2026-09-30

## Current state

V4.3 asynchronous local Evidence analysis is implemented and runtime validated on Ubuntu.

Validated properties:

- canonical Evidence ingestion does not wait for DeepSeek;
- material Evidence is enqueued asynchronously;
- local DeepSeek worker is separate and lower priority;
- degraded local dossiers are excluded from senior context;
- canonical Evidence remains available to OpenClaw/Luna;
- V4.3 staged Ubuntu acceptance returned `V4_3_ACCEPTANCE=PASS`;
- repository CI before the documentation-only Continuous Intelligence update: 594 Python tests PASS and React PASS.

Current development branch:

```text
feature/v4.3-local-evidence-analyst
```

PR:

```text
#65 — feat: V4.3 async local Evidence analyst
base: feature/v4.2-official-sources
state: draft / mergeable
```

Architecture authority:

- `docs/ARCHITECTURE_V4.3.md`
- section 22 defines the Continuous Intelligence Loop.

Do not reopen V4.0–V4.2 deterministic/Evidence authority decisions.

---

## Goal of the next implementation block

Turn V4.3 from a nightly/background analysis capability into a continuously refreshed intelligence service:

```text
new official/public information
        ->
canonical Evidence
        ->
deterministic triage
        ->
bounded async DeepSeek relevance/enrichment
        ->
optional derived dossier
        ->
senior context only when quality-gated
```

The local model is never allowed back onto the critical ingestion path.

---

# P0 — Close CVM Download Múltiplo / Gate D

## P0.1 Configure credentials safely

The user has received a Download Múltiplo login/password directly from CVM.

Required runtime variables:

```text
CVM_DM_USER
CVM_DM_PASS
```

Rules:

- store only in protected runtime env files;
- never paste secrets into GitHub, test fixtures, PR descriptions or logs;
- do not echo the password;
- validate file permissions.

Preferred runtime env locations already used by B3:

```text
/etc/b3-runtime.env
/opt/b3-runtime/b3.env
```

## P0.2 Run live authentication smoke

Use the existing provider:

```text
src/b3_agent/providers/cvm_rad.py
```

Validate:

- credentials accepted;
- request/response XML parsed;
- no-record response handled as normal;
- bad credentials produce explicit authentication failure;
- real disclosures map through Issuer Registry;
- canonical Evidence is produced;
- deterministic materiality runs before any LLM.

## P0.3 Record Gate D

Update:

- `docs/V4.2_OFFICIAL_SOURCES_CHECKPOINT_2026-09-30.md`;
- PR #64.

Expected final V4.2 gate state:

```text
A PASS
B PASS_WITH_COVERAGE_GAPS
C PASS
D PASS
```

Only then decide V4.2 freeze/merge sequencing.

---

# P1 — Durable incremental CVM discovery

## Objective

Convert Download Múltiplo from a one-shot provider into a restart-safe incremental source.

## New component

Recommended:

```text
src/b3_agent/intelligence/discovery_cursor.py
```

Contract should persist:

- last successful requested date/time;
- overlap window;
- last successful retrieval timestamp;
- last source error;
- recently observed provider IDs;
- source/version metadata.

## Required rule

Advance the cursor only after new Evidence has been persisted successfully.

Use an overlap window so restarts/transient failures do not lose documents.

Pseudo-flow:

```text
load cursor
   ->
query cursor-overlap .. now
   ->
normalize + dedupe
   ->
persist canonical Evidence
   ->
enqueue eligible local analysis
   ->
commit cursor
```

Failure before persistence:

```text
DO NOT ADVANCE CURSOR
```

## Tests

Cover:

- first run;
- no new documents;
- duplicate document on overlapping poll;
- source failure;
- process restart;
- same provider ID twice;
- same content hash under repeated retrieval;
- cursor not advanced on persistence failure.

---

# P2 — Continuous discovery job

## New job

Recommended:

```text
src/b3_agent/jobs/continuous_intelligence.py
scripts/run_continuous_intelligence.py
```

Responsibilities:

1. poll authenticated Download Múltiplo;
2. normalize new records to canonical Evidence;
3. map CVM issuer -> ticker deterministically;
4. apply deterministic materiality;
5. persist append-only Evidence;
6. perform deterministic triage;
7. enqueue only eligible local-analysis work;
8. persist discovery metrics/manifest;
9. return without waiting for DeepSeek.

Do not call Ollama inside this job.

---

# P3 — Deterministic prefilter

## Objective

Avoid spending local CPU on every piece of information.

Initial policy:

### Always eligible

```text
official MATERIAL + monitored issuer
```

### Relevance-screen eligible

```text
official CANDIDATE + monitored issuer
high-quality mapped public Evidence + monitored issuer
```

### Skip local analysis

```text
duplicate
NON_MATERIAL
unchanged Evidence fingerprint
unmapped issuer/ticker
out-of-retention-window evidence
low-quality open-web noise
```

The Evidence is still persisted when required by canonical retention rules.

DeepSeek must never change deterministic materiality.

---

# P4 — Split local DeepSeek into two tasks

The PETR4 acceptance showed the larger dossier task can hit `num_predict=768` and become invalid.

Do not solve this only by increasing tokens.

Implement a cheap first stage.

## P4.1 Relevance screen

Recommended contract:

```json
{
  "relevance": "RELEVANT | POSSIBLY_RELEVANT | NOT_RELEVANT | UNKNOWN",
  "themes": [],
  "reason": "",
  "senior_review_candidate": false,
  "evidence_refs": []
}
```

Characteristics:

- structured output / JSON Schema;
- small context;
- small output budget;
- no investment recommendation;
- no prices/probabilities invented;
- no canonical mutation.

Recommended implementation location:

```text
src/b3_agent/intelligence/local_evidence_analysis.py
```

Add a distinct prompt/policy version for relevance screening.

## P4.2 Full local dossier

Run only when:

- deterministic policy says the Evidence is eligible; and
- relevance is `RELEVANT` or `POSSIBLY_RELEVANT`; or
- official MATERIAL policy requires enrichment regardless of local screen.

Important:

> DeepSeek `NOT_RELEVANT` must never suppress official MATERIAL Evidence.

---

# P5 — Scheduler

## Initial conservative cadence

Make cadence configurable through environment.

Recommended first production policy:

```text
Download Múltiplo discovery:
    every 15 minutes on business days during active monitoring window

local relevance/dossier worker:
    separate bounded queue drain after discovery
    one heavy local inference at a time

Open Data reconciliation:
    once daily

restart catch-up:
    cursor overlap + persistent timer
```

Do not hard-code the policy in domain code.

Suggested env variables:

```text
B3_INTEL_DISCOVERY_INTERVAL_MINUTES=15
B3_INTEL_CURSOR_OVERLAP_MINUTES=30
B3_INTEL_LOCAL_BATCH_LIMIT=5
B3_INTEL_RECONCILIATION_HOUR=...
```

Use systemd timers and `Persistent=true`.

Do not install final production timers until P0-P4 tests pass.

---

# P6 — Shared B3 / João Ollama lock

Continuous scheduling makes this mandatory.

Both projects share the same Ollama daemon.

Implement one cross-project lock contract, for example:

```text
/var/lock/local-reasoning.lock
```

Behavior:

- acquire before heavy Ollama inference;
- only one B3/João heavy inference at a time;
- bounded wait;
- if unavailable, requeue/defer;
- never block canonical Evidence ingestion;
- never block deterministic B3 API endpoints;
- never block OpenClaw/Luna interactive reasoning.

This change must be coordinated in both repositories.

Do not implement a B3-only lock and call the problem solved.

---

# P7 — Backend observability

Add read-only endpoints:

```text
GET /intelligence/local/status
GET /intelligence/local/queue
GET /intelligence/local/{ticker}
GET /intelligence/local/manifest
```

Recommended payloads expose:

- queue depth;
- oldest pending age;
- running analysis;
- last completed analysis;
- READY/DEGRADED/FAILED counts;
- local model;
- quality flags;
- Evidence fingerprint;
- latest accepted dossier;
- last Download Múltiplo poll;
- cursor timestamp;
- last source error;
- last Open Data reconciliation.

Do not expose credentials.

---

# P8 — Daily reconciliation

Keep CVM Dados Abertos as an independent reconciliation source.

Daily job should compare:

```text
Download Múltiplo observed Evidence
            vs
Open Data IPE/FCA/CAD
```

Detect:

- records missed by incremental discovery;
- issuer/security mapping changes;
- later historical availability;
- duplicates;
- inconsistent metadata.

Reconciliation may add missing canonical Evidence but must preserve PIT semantics:

```text
historically reconstructed != observed live
```

---

# P9 — Acceptance suite

Before declaring Continuous Intelligence operational, prove these cases on Ubuntu:

1. authenticated Download Múltiplo query succeeds;
2. zero-record query is normal;
3. one real new record maps to canonical issuer/ticker;
4. deterministic materiality occurs before LLM;
5. ingestion completes with zero inline DeepSeek calls;
6. repeated poll creates no duplicate Evidence;
7. restart resumes from cursor with overlap;
8. candidate Evidence reaches relevance queue;
9. relevance screen returns valid structured output;
10. invalid/truncated DeepSeek output becomes DEGRADED;
11. official MATERIAL is never suppressed by local relevance;
12. local worker respects shared B3/João lock;
13. senior context works while DeepSeek is busy/unavailable;
14. observability endpoints reflect queue/cursor state;
15. Open Data reconciliation detects/reconciles a deliberately missing record.

---

# P10 — Merge/freeze sequence

Do not merge out of order.

Recommended sequence:

```text
PR #64 V4.2
    |
    +--> Gate D PASS
    +--> V4.2 checkpoint/freeze
    +--> merge to fix/react-portfolio-api
            |
            v
PR #65 V4.3
    |
    +--> rebase/update base if necessary
    +--> Continuous Intelligence acceptance
    +--> final CI
    +--> V4.3 operational checkpoint
    +--> merge
```

After backend closure:

```text
BACKEND CLOSED
      |
      v
React product integration
```

---

## Do not do in the next chat

- do not reopen V4.0 architecture;
- do not put DeepSeek inline again;
- do not let DeepSeek decide canonical materiality;
- do not send every web result directly to DeepSeek;
- do not install final timers before Gate D + incremental-discovery tests;
- do not expose CVM credentials in chat output, Git, logs or PR text;
- do not merge PR #65 before respecting its V4.2 base sequencing.

---

## First action in the next chat

Start with **P0 only**:

1. verify branch/PR state;
2. inspect existing `cvm_rad.py` and Gate D acceptance tooling;
3. configure/validate runtime credential presence without printing secrets;
4. run a minimal authenticated Download Múltiplo smoke;
5. if it passes, record Gate D before writing the continuous polling job.

Do not begin P1 until P0 is recorded as PASS or a precise external blocker is identified.
