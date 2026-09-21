from fastapi.testclient import TestClient

from b3_agent.server import app


def test_runtime_status_endpoint() -> None:
    client = TestClient(app)

    response = client.get("/runtime/status")

    assert response.status_code == 200

    payload = response.json()

    assert "runtime" in payload
    assert "resources" in payload
    assert "services" in payload
    assert payload["services"]["qdrant"] == "disabled"
    assert payload["services"]["neo4j"] == "disabled"
