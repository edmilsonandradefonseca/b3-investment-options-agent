# V4 Runtime Integration & Calibration

## Canonical local infrastructure
Use `infra/docker-compose.yml` as the single supported local compose stack. It pins Qdrant and Neo4j versions, declares persistent volumes, health checks and the required Neo4j credential.

`infra/qdrant/docker-compose.yml` is legacy/special-purpose and MUST NOT be used for the integrated V4 runtime because it uses an unpinned `latest` Qdrant image and omits Neo4j.

## Preconditions
- Python 3.14 virtual environment
- Docker + Compose plugin
- `infra/.env` created locally from `infra/.env.example` with a non-default Neo4j password
- repository synchronized to the runtime-validation commit/branch
- private portfolio/transaction files remain outside Git

## Validation sequence
1. `docker compose --env-file infra/.env -f infra/docker-compose.yml config`
2. `docker compose --env-file infra/.env -f infra/docker-compose.yml up -d`
3. wait for Qdrant and Neo4j health checks
4. install project + dev dependencies into `.venv`
5. run full pytest regression
6. run explicit Qdrant adapter smoke test against localhost
7. run explicit Neo4j adapter smoke test against localhost
8. start Streamlit and validate BTG upload + dashboard surfaces
9. only after runtime health, begin provider adapters and real-data calibration

## Runtime defaults
- Qdrant REST: `http://127.0.0.1:6333`
- Qdrant gRPC: `127.0.0.1:6334`
- Neo4j Browser/HTTP: `http://127.0.0.1:7474`
- Neo4j Bolt: `bolt://127.0.0.1:7687`

## Vector contract
V4 production collections use 768-dimensional dense embeddings and hybrid dense+sparse retrieval. Tests may use smaller dimensions only as isolated fixtures. Runtime creation must therefore pass `vector_size=768, hybrid=True` to `QdrantVectorStore`.

## Authority
SQLite/Parquet remain canonical structured truth. Qdrant and Neo4j are rebuildable projections; successful service startup does not transfer canonical ownership to either database.