# Local infrastructure — Qdrant + Neo4j

This project keeps the knowledge infrastructure local. Qdrant and Neo4j run in the user's Ubuntu VM under Docker and are consumed by the B3 Agent running on Windows.

## Versions

- Qdrant `v1.19.1`
- Neo4j Community `2026.08.1`
- Python driver: `neo4j>=6,<7`

These are pinned intentionally for reproducible local development. Qdrant exposes REST on `6333` and gRPC on `6334`; Neo4j exposes Browser HTTP on `7474` and Bolt on `7687`.

## Ubuntu VM — first setup

```bash
cd /path/to/b3-investment-options-agent
cp infra/.env.example infra/.env
nano infra/.env
```

Set a real local password in `infra/.env`:

```text
NEO4J_PASSWORD=<your-local-password>
```

Then start the databases:

```bash
docker compose --env-file infra/.env -f infra/docker-compose.yml pull
docker compose --env-file infra/.env -f infra/docker-compose.yml up -d
```

Check status:

```bash
docker compose --env-file infra/.env -f infra/docker-compose.yml ps
```

Check Qdrant:

```bash
curl http://localhost:6333/healthz
```

Open Neo4j Browser from a machine that can reach the VM:

```text
http://<UBUNTU_VM_IP>:7474
```

Bolt endpoint for the application:

```text
neo4j://<UBUNTU_VM_IP>:7687
```

Credentials:

```text
user: neo4j
password: value configured in infra/.env
```

## Windows → Ubuntu VM connectivity

The containers are published on the Ubuntu VM interfaces. The Windows host must be able to reach the VM IP on ports `6333`, `7474` and `7687`.

For a VirtualBox NAT setup, configure host-to-guest port forwarding if necessary. For a bridged/host-only setup, use the VM IP directly.

Do not expose these ports to the public Internet. This is a local development environment.

## Persistence

Docker named volumes preserve the databases across container recreation:

- `qdrant_data`
- `neo4j_data`
- `neo4j_logs`
- `neo4j_import`

Do not run `docker compose down -v` unless the intention is to destroy the local database data.

## Next implementation block

This deployment is only the infrastructure layer. The next code blocks are:

1. Qdrant client configuration and connection health check.
2. Real semantic embedding provider (deterministic embeddings remain test-only).
3. Neo4j persistent `KnowledgeGraphStore` implementation behind the existing abstraction.
4. Real-data ingestion with idempotency, provenance and point-in-time validation.
5. Integration test against local Qdrant + Neo4j.

No dashboard access to either database is introduced; the application remains responsible for orchestration and `KnowledgeContext`.
