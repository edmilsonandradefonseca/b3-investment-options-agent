# Local LLM Router Experiment — Session Checkpoint 2026-09-27

## Purpose
Evaluate whether the Ubuntu host can run a local DeepSeek model alongside B3 Investment & Options Agent and Joao Resolve, and whether a local model can become the first-stage task router to reduce unnecessary remote LLM/API usage.

This experiment does **not** reopen the frozen B3 Architecture V4. The router/model-serving layer is an incremental runtime optimization above the verified backend.

## Host / runtime observed
- Ubuntu 26.04.1 LTS
- Intel Core i7-1185G7, 4 cores / 8 threads
- ~14.8 GiB RAM; 4 GiB swap
- Intel Iris Xe; Ollama currently CPU-only
- Ollama 0.34.4 on 127.0.0.1:11434
- B3 runtime, Joao services, shared 768d embedding, Qdrant, Neo4j and related services remained present.

## Important memory finding
/tmp is tmpfs and had accumulated ~4.3 GiB of OpenClaw temporary build/model-catalog files. Controlled cleanup of `/tmp/openclaw-plugin-build-*` and `/tmp/openclaw-model-catalog-*` reduced /tmp usage to ~268 MiB and raised available RAM to roughly 9 GiB without disrupting checked B3/Joao services.

Follow-up: prevent recurrent OpenClaw temporary build/catalog accumulation in tmpfs.

## DeepSeek experiments

### deepseek-r1:7b
- ~4.7 GB model; fits in memory with B3/Joao active.
- PETR4 current price -> DETERMINISTIC, correct, ~37 s.
- Summarize three supplied news articles -> COMPLEX_LLM, incorrect (expected LOCAL_LLM), ~59 s.
- Portfolio + options + macro + strategies -> COMPLEX_LLM, correct, ~43 s.
- Attempts to suppress reasoning did not eliminate it.
- Direct `/api/chat` with `"think": false` still returned populated `message.thinking`.
- Minimal OK test: ~27.8 s total; 236 eval tokens; ~27.48 s evaluation.
- Conclusion: unsuitable as fast first-stage router on this host/configuration.

### deepseek-r1:8b
- ~5.2 GB model.
- Direct `/api/chat` with `"think": false` still returned populated `message.thinking`.
- Minimal OK test: ~29.32 s total; ~5.55 s load; 178 eval tokens; ~23.36 s evaluation.
- Conclusion: does not solve routing latency/reasoning overhead.

## Current direction

```text
B3 / JOAO TASK
      |
      v
 FAST ROUTER
      |
      +--> DETERMINISTIC --> BRAPI / OPLAB / BCB / DB / calculations / tools
      |
      +--> LOCAL_LLM -----> fast local non-reasoning model
      |
      +--> COMPLEX_LLM ---> JOAO / OPENCLAW
                               |
                               v
                         OAuth / Plus / Codex
                               |
                         availability / limits
                               |
                         OpenAI API fallback
```

DeepSeek-R1 should not classify every request. Deterministic routing rules should resolve obvious tool/API/calculation requests first. A small fast non-reasoning local model should handle ambiguous classification and simple language work. Complex reasoning continues to Joao/OpenClaw.

## Next steps
1. Remove `deepseek-r1:8b` if still installed; keep Ollama.
2. Recheck baseline RAM/swap/load and health of B3/Joao/shared services.
3. Select 2-3 small non-reasoning local candidates for i7-1185G7 / ~15 GiB RAM, preferably ~0.5B-3B.
4. Create a fixed benchmark: market/API request, calculation, summarization, extraction/classification, rewriting, simple reasoning, portfolio/macro strategy, multi-step/multi-agent task.
5. Measure routing accuracy, cold/warm latency, RAM/RSS, CPU and output-format compliance.
6. Target <2-3 s routing latency; ideal <1 s for simple classifications.
7. Implement deterministic rules before LLM fallback.
8. Select a local model only after benchmarks; do not integrate prematurely.
9. Prototype a stable router contract: DETERMINISTIC / LOCAL_LLM / COMPLEX_LLM.
10. Integrate as a runtime layer without reopening frozen B3 V4.
11. Separately evaluate a larger local model as local executor for summarization/extraction/rewrite.
12. Investigate/prevent OpenClaw temp build/model-catalog accumulation in /tmp tmpfs.

## End-of-session decision
Memory capacity is sufficient for local-model experimentation. The primary DeepSeek-R1 7B/8B bottleneck is CPU inference plus unsuppressed reasoning overhead, not RAM. Next experiment: deterministic-first routing plus a small non-reasoning model.
