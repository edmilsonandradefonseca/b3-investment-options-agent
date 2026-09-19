from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from b3_agent.api import server
from b3_agent.repositories.option_contract_registry import OptionContractRecord, OptionContractRegistry
from b3_agent.repositories.option_ledger import OptionTransactionLedger
from b3_agent.schemas.option_transaction import OptionTransaction


def test_options_analytics_returns_lifecycle_and_transaction_drilldown(tmp_path, monkeypatch):
    ledger_path = tmp_path / "ledger.sqlite3"
    registry_path = tmp_path / "contracts.sqlite3"
    monkeypatch.setattr(server, "LEDGER_PATH", ledger_path)
    monkeypatch.setattr(server, "REGISTRY_PATH", registry_path)

    OptionTransactionLedger(ledger_path).append(
        (
            OptionTransaction(
                transaction_id="t1",
                option_ticker="PETRK376",
                broker="BTG",
                quantity=-1000,
                average_cost=13.49,
                total_cost=-13490,
                as_of=date(2026, 8, 1),
                source_type="BROKERAGE_NOTE",
                source_id="n1",
            ),
            OptionTransaction(
                transaction_id="t2",
                option_ticker="PETRK376",
                broker="BTG",
                quantity=1000,
                average_cost=12.00,
                total_cost=12000,
                as_of=date(2026, 8, 15),
                source_type="BROKERAGE_NOTE",
                source_id="n2",
            ),
        )
    )
    OptionContractRegistry(registry_path).upsert(
        OptionContractRecord(
            option_ticker="PETRK376",
            expiration_date=date(2026, 9, 18),
            option_type="PUT",
            strike=37.60,
            underlying_ticker="PETR4",
            contract_multiplier=1.0,
            source_ref="test",
        )
    )

    response = TestClient(server.app).get(
        "/api/options/analytics",
        params={"underlying": "PETR4", "option_type": "PUT"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["realized_pnl"] == 1490.0
    assert body["summary"]["lifecycle_count"] == 1
    assert len(body["lifecycles"]) == 1
    assert len(body["transactions"]) == 2
    assert body["transactions"][0]["source_type"] == "BROKERAGE_NOTE"
