# V4 Retrieval Benchmark Gate

**Status:** IMPLEMENTED — calibration corpus pending production data

V4 now contains a provider-neutral retrieval benchmark harness for comparing retrieval profiles without hard-coding a preferred profile.

Metrics captured:
- Precision@K
- Recall@K
- MRR
- NDCG@K
- mean retrieval latency

Profiles may include dense-only, dense+sparse/RRF and deterministic reranking. The benchmark reports measurements; profile selection remains a calibration decision based on labeled B3 queries and latency constraints.

The synthetic CI tests validate metric correctness. A production-quality labeled corpus is intentionally not fabricated in code; it must be built from real B3 queries/evidence during end-to-end validation.
