# V4 Runtime Integration & Calibration

## Runtime topology: Shared AI Platform

B3 does not own duplicate infrastructure services. It consumes the same local AI platform used by João Resolve and future agents.

Shared services:

- multilingual embedding service: `http://127.0.0.1:8093`
- Qdrant REST: `http://127.0.0.1:6333`
- Neo4j Bolt: `bolt://127.0.0.1:7687`
- SearXNG: `http://127.0.0.1:8080`
- future local LLM runtime (for example DeepSeek): shared by consumers through an explicit service contract

The B3 repository is a consumer of these services. Its preflight MUST NOT start, stop, restart, recreate or upgrade shared platform services.

## Isolation contract

Shared infrastructure does not imply shared application data.

### Qdrant

Collections are application-owned. B3 collections must use the `b3_` prefix and João collections use `joao_`.

The existing `b3_memory_768` collection is a legacy dense-only collection and must not silently become the V4 hybrid evidence collection.

The V4 RAG/vector contract requires:

- 768-dimensional dense vectors
- named dense vector `dense`
- named sparse vector `sparse`
- hybrid dense+sparse retrieval
- Qdrant RRF fusion

A V4 production collection should therefore use an explicit name such as `b3_evidence_768_hybrid`.

### Neo4j

The shared Neo4j database uses logical schema isolation.

- João nodes: `Entity`
- B3 nodes: `B3Entity`
- B3 constraint: `b3_entity_id`

B3 graph queries and mutations must remain scoped to `B3Entity`. B3 must never delete or rewrite João `Entity` nodes as part of initialization, smoke testing or rebuild operations.

## Embedding contract

The shared runtime embedding service is the canonical embedding provider for the local platform.

Validated runtime contract on 2026-09-27:

- model: `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`
- dimensions: 768
- normalized sentence-transformer embeddings
- health endpoint: `GET /health`
- single embedding endpoint: `POST /embed`

B3 must validate the returned dimension before writing to Qdrant.

## Configuration

Default endpoints:

- `B3_EMBEDDING_URL=http://127.0.0.1:8093`
- `B3_QDRANT_URL=http://127.0.0.1:6333`
- `B3_NEO4J_URI=bolt://127.0.0.1:7687`
- `B3_NEO4J_USER=neo4j`

Secrets remain local and are never committed. The preflight resolves `NEO4J_PASSWORD` in this order:

1. current environment
2. local `infra/.env`
3. shared platform environment selected by `B3_SHARED_PLATFORM_ENV` (current Ubuntu default: `/opt/joao-runtime/joao.env`)

The current default shared-env path is a deployment detail, not application ownership. A later platform extraction may move it without changing the B3 domain architecture.

## Validation sequence

Run:

```bash
bash scripts/runtime_preflight.sh
```

The script:

1. validates the B3 Python environment
2. loads only the credential needed to connect to shared Neo4j
3. runs the complete pytest regression
4. validates the live 768d embedding service
5. creates and deletes only a temporary B3-prefixed hybrid Qdrant smoke collection
6. verifies shared Neo4j connectivity and the B3 `B3Entity` adapter
7. does not manage shared service lifecycle

After the preflight succeeds, start the dashboard and validate BTG upload and V4 surfaces.

## Legacy compose

`infra/docker-compose.yml` is retained only as a historical/isolated-development reference. It is not part of the canonical Ubuntu V4 runtime and must not be executed on the shared host because the standard Qdrant and Neo4j ports are already owned by the Shared AI Platform.

## Authority

SQLite/Parquet remain canonical structured truth. Qdrant and Neo4j are rebuildable projections. Sharing their service processes does not transfer canonical ownership of B3 data or permit cross-application writes.

## Future local LLM

The future DeepSeek runtime follows the same platform rule: one reusable local inference service, multiple consumers, explicit routing/contracts, and application-level isolation. B3 and João may both use it without loading duplicate model instances.
