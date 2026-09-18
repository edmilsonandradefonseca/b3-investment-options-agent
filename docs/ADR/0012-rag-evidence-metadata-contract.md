# ADR 0012 — RAG Evidence & Metadata Contract

**Status:** Accepted  
**Date:** 2026-09-17  
**Scope:** RAG foundation, market evidence, temporal retrieval and provenance

## Decision

Introduce a canonical `Evidence` contract with typed `EvidenceMetadata` as the boundary between source acquisition and the RAG/KG processing pipeline.

The contract preserves provenance, publication/retrieval timestamps, asset and event references, validity intervals, confidence, retention class and decay profile.

## Required metadata

Each evidence record carries:

- `document_id`
- `source`
- `published_at` when applicable
- `retrieved_at`
- `ticker_refs`
- `sector_refs`
- `event_refs`
- `topic`
- `source_quality`
- `confidence`
- `valid_from` / `valid_to` when applicable
- `retention_class`
- `decay_profile`

An optional `extra` map allows provider-specific metadata without changing the canonical contract.

## Point-in-time rule

Evidence is available for a decision only when its publication/retrieval timestamps and validity interval permit use at the requested `as_of` timestamp.

Future evidence must never be returned as evidence for an earlier decision.

## Provenance

`evidence_id` identifies the canonical evidence object. `source_ref` is preserved from the metadata source and may point to an external publisher, Obsidian note or another evidence store.

URLs are optional but, when present, must be absolute HTTP(S) URLs.

## Lifecycle integration

Evidence carries the existing lifecycle classifications. The RAG contract does not decide physical retention; `InformationLifecycleEngine` remains authoritative for retention and freshness policy.

Current policy:

- stock market: 360 days;
- options market: 90 days;
- market evidence: 90 days;
- active market events: no fixed expiry;
- decisions and persistent knowledge: permanent.

## Normalization

Ticker references are normalized to uppercase and duplicate references are removed deterministically. Confidence is bounded to `[0, 1]`. All timestamps must be timezone-aware.

## Boundaries

This contract does not implement embeddings, vector storage, semantic ranking or LLM enrichment. Those are subsequent RAG Foundation blocks.

It also does not replace deterministic market-data contracts or analytical engines.
