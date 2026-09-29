from datetime import date
from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from b3_agent import server
from b3_agent.schemas.position import PortfolioContext, Position
from b3_agent.schemas.option_transaction import OptionTransaction
from b3_agent.repositories.option_ledger import OptionTransactionLedger

client = TestClient(server.app)


def test_capital_profile_persists_and_validates_reserve(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "settings", replace(server.settings, data_dir=tmp_path))
    assert client.get("/capital-profile").json()["status"] == "NOT_AVAILABLE"
    assert client.post("/capital-profile", json={"available_capital": 1000, "minimum_reserve": 1200}).status_code == 400
    response = client.post("/capital-profile", json={"available_capital": 1000, "minimum_reserve": 200})
    assert response.status_code == 200
    assert client.get("/capital-profile").json()["usable_capital"] == 800
    assert (tmp_path / "b3_agent.db").exists()
    assert not (tmp_path / "capital_profile.sqlite3").exists()


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
    assert response.json()["intelligence"]["as_of"] == "2026-09-29"


def test_brokerage_note_cash_flow_preserves_side_and_provenance(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "settings", replace(server.settings, data_dir=tmp_path))
    assert client.get("/options/ledger").json()["status"] == "NOT_AVAILABLE"
    ledger = OptionTransactionLedger(tmp_path / "options.sqlite3")
    ledger.append((OptionTransaction(transaction_id="note:1", option_ticker="ABEVV153", broker="BTG", quantity=-2000, average_cost=0.42, total_cost=-840, as_of=date(2026, 9, 28), note_number="123", source_type="BROKERAGE_NOTE", source_ref="BTG:NotaCorretagem:123"),))
    result = client.get("/options/ledger")
    assert result.status_code == 200
    assert result.json()["operations"][0]["cash_flow"] == 840
    assert result.json()["operations"][0]["note_number"] == "123"
