# B3 Investment & Options Agent — Status and Local-AI Routing Next Steps

**Date:** 2026-09-27  
**Status:** Architecture direction recorded; implementation not started.  
**Important:** The V4 backend functional freeze remains valid. This document defines the next runtime/LLM integration phase and does not reopen the frozen domain architecture.

## 1. Status reached today

### Backend and runtime
- V4 backend remains functionally frozen with the existing UC01–UC12 acceptance baseline.
- Ubuntu runtime was restored with `b3-runtime`, systemd integration and `/runtime/status`.
- B3 API is reachable from the Windows host over the LAN after binding the API to `0.0.0.0:8000`.
- Shared embedding service is operational at `127.0.0.1:8093`, using the 768-dimensional multilingual embedding contract.
- Qdrant and Neo4j shared dependencies are operational.
- OPLAB and BRAPI credentials were persisted in the local runtime environment without committing secrets.
- The React/Tauri Windows desktop application build is available and can connect to the Ubuntu backend.

### LLM/runtime finding
A real `/orchestrate` call reached the B3 workflow and initialized it successfully, but the Market Agent failed when the OpenAI Python SDK called the Responses API because the API account had no remaining credit (`429 credit_balance_exhausted`).

This confirms:
1. the B3 runtime and workflow reached the LLM boundary;
2. the current B3 LLM path depends directly on paid OpenAI API billing;
3. ChatGPT Plus/Codex subscription usage is a different resource from OpenAI API credit;
4. the current failure should eventually be converted from an HTTP 500 into a structured/degraded response.

### João Resolve / OpenClaw finding
The João/OpenClaw environment has previously executed model work through ChatGPT/Codex OAuth subscription usage rather than an OpenAI API key. This suggests an alternative execution path for tasks that can legitimately be delegated through OpenClaw instead of calling the paid API directly.

## 2. New direction: local-first AI routing

The next phase should move away from the assumption that every LLM task goes directly to a paid API.

Target logical flow:

```text
                       B3 TASK
                          |
                          v
                  LOCAL AI ROUTER
              (candidate: DeepSeek)
                          |
          +---------------+----------------+
          |               |                |
          v               v                v
   deterministic       local LLM       complex reasoning
 BRAPI/OPLAB/BCB/      simple work             |
 calculations/etc.                            v
                                      JOÃO / OPENCLAW
                                             |
                                            OAuth
                                             |
                                        Plus / Codex
                                             |
                                            Luna
                                             |
                                   subscription limit
                                             |
                                   if unavailable/unsuitable
                                             v
                                       OpenAI API
                                          fallback
```

The same local-first principle should eventually serve both **B3** and **João Resolve**, instead of maintaining two unrelated LLM strategies.

## 3. Architectural principles

1. **Deterministic before generative.** If a task can be answered by BRAPI, OPLAB, BCB, calculations, databases, retrieval, rules or existing services, do not spend LLM tokens.
2. **Local before paid remote inference where quality permits.** A local model should handle routing, classification, extraction, summarization and other validated low/medium-complexity work.
3. **Do not let the local model be the sole judge of its own competence.** Routing must combine deterministic policy, task metadata, model confidence and observed quality.
4. **OpenClaw/Codex is an escalation path, not a fake API key.** Do not attempt to reuse OAuth credentials as an OpenAI API credential.
5. **OpenAI API remains a controlled fallback.** It is useful when OpenClaw subscription capacity is unavailable, unsuitable for the execution mode, or when a stable programmatic API is required.
6. **B3 must degrade gracefully.** Loss of a remote LLM must not make deterministic market/risk/portfolio capabilities unavailable.
7. **Shared AI Platform.** If a local LLM is adopted, prefer one shared service for João and B3, similar to the shared embedding service, rather than loading duplicate models.
8. **Measure before optimizing.** Route decisions must eventually be backed by latency, memory, quality, token and cost telemetry.

## 4. DeepSeek hypothesis — not yet approved for production

DeepSeek is a **candidate**, not yet the final local model.

Before adoption we must validate:
- available Ubuntu RAM/CPU while João, B3, Qdrant, Neo4j, embedding and other shared services are running;
- memory pressure and swap behavior;
- model load time;
- tokens/second;
- first-token latency;
- concurrent-request behavior;
- context-window memory impact;
- JSON/structured-output reliability;
- routing/classification accuracy;
- summarization quality;
- Portuguese and English quality;
- tool-calling reliability if tool execution is required.

Important design caution: small/quantized local reasoning models may be adequate for routing and text reasoning while being unreliable as universal agentic tool executors. Therefore **router model** and **tool-execution model** are separate roles even if one model eventually proves capable of both.

## 5. Proposed target architecture

```text
                       User / Scheduler / Event
                                  |
                                  v
                         JOÃO / ENTRY LAYER
                                  |
                                  v
                        ROUTING POLICY ENGINE
                         /                \
                deterministic          local model
                    rules             classification
                         \              /
                          v            v
                           ROUTE DECISION
                                  |
       +--------------------------+--------------------------+
       |                          |                          |
       v                          v                          v
 deterministic services      local inference         remote escalation
 BRAPI / OPLAB / BCB /       cheap/simple tasks              |
 DB / Qdrant / Neo4j                                       OpenClaw
                                                             |
                                                      ChatGPT/Codex OAuth
                                                             |
                                                    if unavailable/unsuitable
                                                             |
                                                             v
                                                       OpenAI API
                                                         fallback
```

For B3 specifically, João should remain an orchestration/entry boundary and must not bypass B3 domain contracts by directly mutating B3 SQLite/Parquet/Qdrant/Neo4j state.

## 6. Next steps — execution order

### Phase A — capacity baseline (no architecture changes)
1. Inventory Ubuntu CPU, RAM, swap, disk and current service memory.
2. Measure idle and representative-load consumption of João, B3, embedding, Qdrant, Neo4j, SearXNG and related services.
3. Establish a safe RAM headroom target so local inference cannot destabilize B3/João.
4. Identify the unknown listeners currently using ports 8091/8092 before changing them.

**Go/no-go:** determine the maximum safe local model size/quantization.

### Phase B — isolated local-LLM proof of concept
1. Install a local inference runtime without modifying B3 V4 contracts.
2. Start with a model that safely fits the measured capacity.
3. Benchmark routing/classification, JSON output, PT/EN summarization and representative João/B3 prompts.
4. Record RAM, CPU, tokens/s, time-to-first-token and failure rate.
5. Compare at least one alternative model if DeepSeek tool/structured-output behavior is inadequate.

**Go/no-go:** local model must provide acceptable latency and routing quality without starving production services.

### Phase C — router contract
Define a model-independent routing response, e.g.:

```json
{
  "route": "deterministic|local|openclaw|openai_api",
  "complexity": "low|medium|high",
  "requires_tools": true,
  "requires_market_data": true,
  "confidence": 0.92,
  "reason_code": "..."
}
```

Add deterministic overrides so critical/high-risk classes cannot be incorrectly downgraded solely because the local model claims high confidence.

### Phase D — João/OpenClaw integration
1. Make local inference the default for validated low-cost task classes.
2. Escalate complex/agentic tasks to OpenClaw/Codex where appropriate.
3. Preserve OpenAI API as explicit fallback.
4. Add timeout/circuit-breaker behavior.
5. Ensure subscription exhaustion does not create endless retries.

### Phase E — B3 integration
1. Introduce an LLM-provider/routing abstraction at the existing B3 LLM boundary.
2. Preserve deterministic/statistical ownership of measurable facts.
3. Route only validated task classes to local inference.
4. Delegate eligible complex reasoning through the João/OpenClaw boundary.
5. Use OpenAI API only when policy requires it or other paths are unavailable.
6. Convert quota/provider failures into structured degraded states instead of HTTP 500.

### Phase F — telemetry and optimization
Record at minimum:
- request/task ID;
- application (B3/João);
- use case/agent;
- selected route/provider/model;
- input/output tokens where available;
- latency;
- success/failure/fallback;
- estimated API cost;
- routing confidence;
- quality/evaluation result.

Use these measurements to decide whether Plus/Codex capacity, local inference and API fallback are being used economically.

## 7. Explicit non-goals for the next session

- Do not reopen the frozen V4 business/domain architecture.
- Do not remove OpenAI API support before fallback behavior is proven.
- Do not expose or commit API keys/OAuth credentials.
- Do not make DeepSeek production-default before capacity and quality benchmarks.
- Do not let a local LLM invent market facts that belong to deterministic data services.
- Do not make OpenClaw a direct writer to B3 canonical stores.

## 8. First task for the next session

**Start with Ubuntu capacity measurement, not installation.**

Collect a reproducible baseline of CPU/RAM/swap and per-service memory under normal João+B3 operation. From that evidence, choose the first local model and quantization to test. Only after the benchmark passes should the routing architecture be implemented.

## 9. Success criteria

The migration is successful when:
- João and B3 remain stable under concurrent normal load;
- routine LLM work is served locally when quality is sufficient;
- deterministic tasks never consume LLM quota unnecessarily;
- complex tasks can escalate to OpenClaw/Codex;
- API is a controlled fallback rather than the default for every task;
- provider/quota failure degrades gracefully;
- routing decisions and costs are observable;
- B3 V4 functional behavior remains regression-tested and unchanged.
