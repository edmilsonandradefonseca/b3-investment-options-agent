#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
echo "===== B3 V4 RUNTIME PREFLIGHT ====="
python3 --version
docker --version
docker compose version
test -f infra/.env || { echo "ERROR: infra/.env missing. Copy infra/.env.example and set NEO4J_PASSWORD."; exit 2; }
docker compose --env-file infra/.env -f infra/docker-compose.yml config >/dev/null
echo "compose config: OK"
docker compose --env-file infra/.env -f infra/docker-compose.yml up -d
for i in {1..30}; do
  q="$(docker inspect -f '{{.State.Health.Status}}' b3-qdrant 2>/dev/null || true)"
  n="$(docker inspect -f '{{.State.Health.Status}}' b3-neo4j 2>/dev/null || true)"
  echo "attempt=$i qdrant=$q neo4j=$n"
  [[ "$q" == "healthy" && "$n" == "healthy" ]] && break
  sleep 2
done
[[ "$(docker inspect -f '{{.State.Health.Status}}' b3-qdrant)" == "healthy" ]]
[[ "$(docker inspect -f '{{.State.Health.Status}}' b3-neo4j)" == "healthy" ]]
test -x .venv/bin/python || { echo "ERROR: .venv/bin/python missing."; exit 3; }
.venv/bin/python --version
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest
.venv/bin/python - <<'PY'
from qdrant_client import QdrantClient
from b3_agent.knowledge.qdrant_store import QdrantVectorStore
client=QdrantClient(url="http://127.0.0.1:6333")
store=QdrantVectorStore(client=client,collection_name="b3_runtime_smoke_768",vector_size=768,hybrid=True)
assert store.count() == 0
client.delete_collection("b3_runtime_smoke_768")
print("QDRANT 768D HYBRID SMOKE OK")
PY
set -a
source infra/.env
set +a
.venv/bin/python - <<'PY'
import os
from neo4j import GraphDatabase
from b3_agent.knowledge.neo4j_store import Neo4jKnowledgeGraphStore
driver=GraphDatabase.driver("bolt://127.0.0.1:7687",auth=("neo4j",os.environ["NEO4J_PASSWORD"]))
driver.verify_connectivity()
store=Neo4jKnowledgeGraphStore(driver)
assert store.count_entities() >= 0
driver.close()
print("NEO4J SMOKE OK")
PY
echo "===== RUNTIME PREFLIGHT PASSED ====="
echo "Next: streamlit run mvp/dashboard/app.py"
