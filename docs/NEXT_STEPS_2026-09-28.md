# B3 Investment & Options Agent — Next Steps Handoff — 2026-09-28

## Current state

Architecture V4.0 remains frozen and authoritative.

V4.1 is an additive runtime/intelligence layer. The following are implemented:
- deterministic Fast Router;
- real router smoke validation;
- DeepSeek R1 8B as background-only reasoning;
- UC-10 nightly intelligence pilot;
- material-event prefilter;
- freshness hardening;
- bounded sequential DeepSeek batch controls;
- systemd/timer installation path;
- React remains the production frontend direction.

## What should happen next

### 1. Do not reopen V4 architecture

Do not redesign:
- UC-01..UC-12 baseline;
- deterministic/statistical numerical authority;
- PIT rules;
- SQLite/Parquet canonical truth;
- Qdrant/Neo4j roles;
- no autonomous trading;
- human investment authority.

Future work should integrate into the frozen backend.

### 2. Validate B3 + João shared-host resource arbitration

Both projects can use the same Ollama daemon.

The next runtime-hardening task should prevent simultaneous heavy DeepSeek work.

Recommended design:
- one host-level local-reasoning lock/semaphore;
- B3 nightly jobs and João research synthesis both acquire it;
- deterministic services never wait on the local model;
- timeout/skip/defer behavior for low-priority local reasoning;
- record current owner and wait/defer metrics.

Avoid a second LLM router.

### 3. Finish UC-10 production scheduling validation

Confirm the installed nightly timer/service in the real Ubuntu host.

Validate:
- timer enabled;
- intended schedule;
- no DeepSeek call when there is no fresh/material event;
- bounded max DeepSeek calls;
- manifest generated;
- failures isolated per ticker;
- model unloaded afterward;
- no conflict with João background work.

### 4. Add B3 senior escalation path only after UC-10 is stable

For material/conflicting research:
- pass canonical B3 facts + evidence to OpenClaw/Luna;
- DeepSeek summary is secondary context;
- never let the senior LLM become numerical authority;
- persist escalation status and rationale;
- make the result visible to the user as derived intelligence.

Do not use Luna for routine deterministic calculations.

### 5. Continue React production frontend

Do not spend more effort on Streamlit.

Next frontend integration should expose:
- portfolio snapshot;
- options intelligence;
- opportunity discovery;
- what-if;
- research/news intelligence;
- stress/risk;
- provenance/freshness;
- V4.1 derived-intelligence status.

Use typed backend clients and preserve backend authority.

### 6. Validate real B3 use cases end-to-end from React

Priority:
1. UC-01 Portfolio Intelligence;
2. UC-02 Options Intelligence;
3. UC-03 Opportunity Discovery;
4. UC-04 Strategy Comparison / What-if;
5. UC-10 Research, News & Event Intelligence;
6. UC-11 Risk / Stress;
7. UC-12 Copilot.

Do not infer implementation completeness from UI existence alone; validate real data path and errors.

### 7. Close remaining operational gaps

Review:
- BTG note ZIP upload failure path;
- BRAPI/OPLAB runtime environment;
- b3-runtime CLI installation on the intended host;
- nightly timer state;
- React typed client and shell;
- Windows 11 app packaging path;
- PR/runtime branch cleanup.

### 8. Add V4.1 observability

Minimum useful metrics:
- Fast Router route counts;
- ambiguous/OpenClaw fallback count;
- UC-10 ticker completed/skipped/deferred/failed;
- DeepSeek call count/duration;
- local model resource lock owner;
- max RAM impact / model loaded state;
- derived-intelligence freshness;
- escalation count.

### 9. Keep local reasoning bounded

Continue enforcing:
- background only;
- concurrency 1 per host;
- bounded context;
- bounded input;
- no uncontrolled fan-out;
- model unload after inference;
- low CPU priority;
- no canonical persistence of raw LLM claims without validation.

## Current target architecture

```text
B3 TASK
  |
  v
DETERMINISTIC FAST ROUTER
  |
  +--> deterministic engines / APIs / SQL
  |
  +--> background material research
  |       |
  |       v
  |   DeepSeek R1 8B local
  |
  +--> ambiguous / complex
          |
          v
      OpenClaw / Luna
          |
          v
      explanation / senior synthesis

Canonical authority remains in B3 deterministic services.
```

## Suggested first task for the next chat

Read:
1. `docs/ARCHITECTURE_V4.1.md`;
2. this file;
3. current runtime/timer configuration;
4. React next-steps document if present;
5. latest main branch state.

Then answer:

> What is the shortest path to production from the current frozen B3 backend, prioritizing shared-host DeepSeek arbitration, UC-10 scheduling validation and React E2E integration?
