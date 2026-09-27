#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

QDRANT_URL="${B3_QDRANT_URL:-http://127.0.0.1:6333}"
NEO4J_URI="${B3_NEO4J_URI:-bolt://127.0.0.1:7687}"
NEO4J_USER="${B3_NEO4J_USER:-neo4j}"
EMBEDDING_URL="${B3_EMBEDDING_URL:-http://127.0.0.1:8093}"
SHARED_ENV="${B3_SHARED_PLATFORM_ENV:-/opt/joao-runtime/joao.env}"

echo "===== B3 V4 SHARED RUNTIME PREFLIGHT ====="
python3 --version

# Load credentials without owning or starting shared infrastructure.
if [[ -f infra/.env ]]; then
  set -a
  source infra/.env
  set +a
elif [[ -r "$SHARED_ENV" ]]; then
  set -a
  source "$SHARED_ENV"
  set +a
fi

: "${NEO4J_PASSWORD:?NEO4J_PASSWORD must be available in the environment, infra/.env, or B3_SHARED_PLATFORM_ENV}"

echo "shared Qdrant:   $QDRANT_URL"
echo "shared Neo4j:    $NEO4J_URI"
echo "shared embedding:$EMBEDDING_URL"

test -x .venv/bin/python || { echo "ERROR: .venv/bin/python missing."; exit 3; }
.venv/bin/python --version
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest

B3_QDRANT_URL="$QDRANT_URL" B3_EMBEDDING_URL="$EMBEDDING_URL" .venv/bin/python - <<'PY'
import json
import os
import urllib.request

from qdrant_client import QdrantClient
from b3_agent.knowledge.qdrant_store import QdrantVectorStore

embedding_url = os.environ["B3_EMBEDDING_URL"].rstrip("/")
qdrant_url = os.environ["B3_QDRANT_URL"].rstrip("/")

with urllib.request.urlopen(f"{embedding_url}/health", timeout=10) as response:
    health = json.loads(response.read().decode("utf-8"))

assert health.get("status") == "ok", health
assert health.get("dimensions") == 768, health

request = urllib.request.Request(
    f"{embedding_url}/embed",
    data=json.dumps({"text": "B3 shared runtime preflight"}).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(request, timeout=30) as response:
    payload = json.loads(response.read().decode("utf-8"))

vector = payload.get("embedding", [])
assert payload.get("dimensions") == 768, payload
assert len(vector) == 768, len(vector)
print(f"EMBEDDING 768D OK model={health.get('model')}")

client = QdrantClient(url=qdrant_url)
smoke_collection = "b3_runtime_smoke_768_hybrid"

if client.collection_exists(smoke_collection):
    client.delete_collection(smoke_collection)

try:
    store = QdrantVectorStore(
        client=client,
        collection_name=smoke_collection,
        vector_size=768,
        hybrid=True,
    )
    assert store.count() == 0
    info = client.get_collection(smoke_collection)
    vectors = info.config.params.vectors
    sparse = info.config.params.sparse_vectors
    assert "dense" in vectors
    assert vectors["dense"].size == 768
    assert "sparse" in sparse
    print("QDRANT SHARED 768D HYBRID SMOKE OK")
finally:
    if client.collection_exists(smoke_collection):
        client.delete_collection(smoke_collection)
PY

B3_NEO4J_URI="$NEO4J_URI" B3_NEO4J_USER="$NEO4J_USER" .venv/bin/python - <<'PY'
import os

from neo4j import GraphDatabase
from b3_agent.knowledge.neo4j_store import Neo4jKnowledgeGraphStore

driver = GraphDatabase.driver(
    os.environ["B3_NEO4J_URI"],
    auth=(os.environ["B3_NEO4J_USER"], os.environ["NEO4J_PASSWORD"]),
)
try:
    driver.verify_connectivity()
    store = Neo4jKnowledgeGraphStore(driver)
    assert store.count_entities() >= 0
    print("NEO4J SHARED B3Entity NAMESPACE SMOKE OK")
finally:
    driver.close()
PY

echo "===== SHARED RUNTIME PREFLIGHT PASSED ====="
echo "No shared service was started, stopped, restarted or upgraded."
echo "Next: streamlit run mvp/dashboard/app.py"
