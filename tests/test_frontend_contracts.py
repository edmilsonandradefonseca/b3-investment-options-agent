from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from b3_agent import server
from b3_agent.schemas.position import PortfolioContext, Position

client = TestClient(server.app)


def test_capital_profile_persists_and_validates_reserve(tmp_path, monkeypatch):
    monkeypatch.setattr(server.settings, "data_dir", tmp_path)
    assert client.get("/capital-profile").json()["status"] == "NOT_AVAILABLE"
    assert client.post("/capital-profile", json={"available_capital": 1000, "minimum_reserve": 1200}).status_code == 400
    response = client.post("/capital-profile", json={"available_capital": 1000, "minimum_reserve": 200})
    assert response.status_code == 200
    assert client.get("/capital-profile").json()["usable_capital"] == 800


def test_portfolio_read_preserves_canonical_values(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "_import_dir", lambda: tmp_path)
    assert client.get("/portfolio/current").json()["status"] == "NOT_AVAILABLE"
    (tmp_path / "portfolio.xlsx").write_bytes(b"stub")
    snapshot = PortfolioContext(
        as_of=date(2026, 9, 29),
        positions=(Position(position_id="btg:ABEV3", ticker="ABEV3", instrument_type="STOCK", quantity=-7000, average_cost=15.0, market_value=-105000, source_ref="BTG"),),
    )
    monkeypatch.setattr(server.BtgRendaVariavelLoader, "load", lambda self, path: snapshot)
    response = client.get("/portfolio/current")
    assert response.status_code == 200
    assert response.json()["positions"][0]["quantity"] == -7000
    assert response.json()["positions"][0]["market_value"] == -105000
