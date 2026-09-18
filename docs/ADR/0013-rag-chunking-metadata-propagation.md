# ADR 0013 — RAG Chunking + Metadata Propagation

- **Status:** Accepted
- **Date:** 2026-09-17
- **Scope:** RAG foundation, evidence chunking, provenance

## Decision

RAG ingestion will split canonical `Evidence` into deterministic `EvidenceChunk` records before embeddings or vector storage are introduced.

Each chunk preserves the complete `EvidenceMetadata` contract from its parent evidence and adds chunk-local metadata:

- `chunk_index`
- `chunk_count`
- `parent_evidence_id`
- `chunk_content_hash`

Chunk IDs are deterministic and derived from the parent evidence ID, chunk position and SHA-256 content hash. The default chunk size is 1200 characters.

## Chunking rules

1. Prefer paragraph boundaries.
2. If a paragraph exceeds the limit, split on whitespace where possible.
3. A single token longer than the limit may be split deterministically.
4. Do not use an LLM for chunking.
5. Do not embed or persist vectors in this block.
6. Do not alter publication/retrieval timestamps, ticker references, event references, retention class or decay profile during chunking.
7. Chunk metadata must remain sufficient for point-in-time filtering and provenance.

## Rationale

This establishes a stable ingestion boundary for later embedding and hybrid retrieval work. Semantic/vector infrastructure can change without changing the canonical evidence contract or downstream auditability.

## Non-goals

- embeddings
- vector database
- semantic ranking
- LLM enrichment
- news ingestion
- investment recommendations
