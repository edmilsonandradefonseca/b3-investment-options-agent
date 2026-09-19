from datetime import date
from pathlib import Path
from types import SimpleNamespace

from b3_agent.api import server


def test_portfolio_path_uses_same_env_as_streamlit(monkeypatch):
    monkeypatch.setenv("B3_AGENT_PORTFOLIO_FILE", r"C:\data\btg.xlsx")
    monkeypatch.delenv("B3_AGENT_PORTFOLIO_PATH", raising=False)

    assert server._portfolio_snapshot_path() == Path(r"C:\data\btg.xlsx").resolve()


def test_portfolio_endpoint_maps_loader_output(monkeypatch, tmp_path):
    source = tmp_path / "btg.xlsx"
    source.write_bytes(b"placeholder")
    monkeypatch.setenv("B3_AGENT_PORTFOLIO_FILE", str(source))

    positions = (
        SimpleNamespace(
            ticker="PETR4",
            instrument_type="STOCK",
            quantity=2000,
            average_cost=34.10,
            market_price=37.20,
            market_value=74400,
            option_type=None,
            underlying_ticker=None,
            strike=None,
            expiration_date=None,
        ),
        SimpleNamespace(
            ticker="PETRV100",
            instrument_type="OPTION",
            quantity=-1000,
            average_cost=0.50,
            market_price=0.20,
            market_value=-200,
            option_type="CALL",
            underlying_ticker="PETR4",
            strike=40.0,
            expiration_date=date(2026, 10, 16),
        ),
    )
    fake_context = SimpleNamespace(
        as_of=date(2026, 9, 18),
        positions=positions,
        cash=1000.0,
        quality_status="VALIDATED",
    )
    monkeypatch.setattr(server.BtgRendaVariavelLoader, "load", lambda self, path: fake_context)

    payload = server.portfolio_snapshot()

    assert payload["status"] == "OK"
    assert payload["as_of"] == "2026-09-18"
    assert payload["summary"] == {
        "total_value": 75200.0,
        "stock_value": 74400.0,
        "option_value": -200.0,
        "position_count": 2,
    }
    assert payload["positions"][0]["ticker"] == "PETR4"
    assert payload["positions"][1]["pnl"] == 300.0
