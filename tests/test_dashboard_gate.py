from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from b3_agent import server
from b3_agent.config import settings
from b3_agent.options.brokerage_notes import BrokerageNoteParser
from b3_agent.repositories.option_ledger import OptionTransactionLedger
from b3_agent.orchestration import b3_orchestrator
from b3_agent.orchestration import runtime
from b3_agent.portfolio.snapshot import load_active_snapshots
from tests.dashboard_fixtures import make_btg_portfolio, make_options_transactions, make_brokerage_note


def _patch_data_dir(monkeypatch, data_dir: Path) -> None:
    runtime_settings = SimpleNamespace(data_dir=data_dir)
    server_settings = SimpleNamespace(
        data_dir=data_dir,
        obsidian_vault=None,
        llm_enabled=False,
        llm_model="gpt-5.6-luna",
    )
    monkeypatch.setattr(runtime, "settings", runtime_settings)
    monkeypatch.setattr(server, "settings", server_settings)


def test_dashboard_contract_uses_btg_loader_and_orchestrator(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    imports = data_dir / "imports"
    imports.mkdir(parents=True)
    make_btg_portfolio(imports / "portfolio.xlsx")
    make_options_transactions(imports / "options_transactions.xlsx")
    _patch_data_dir(monkeypatch, data_dir)

    server._configure_runtime.cache_clear()
    runtime.configure_dashboard_workflow()

    response = b3_orchestrator(
        task="Carregar snapshot do Dashboard",
        context={"dashboard_view": "portfolio"},
    )

    assert response.status == "COMPLETED"
    snapshot = response.result["dashboard_snapshot"]
    assert set(snapshot) == {
        "portfolio_context",
        "portfolio_intelligence",
        "options_transactions",
        "options_performance",
        "options_reconciliation",
    }
    assert snapshot["portfolio_context"].quality_status == "VALIDATED"
    assert len(snapshot["portfolio_context"].positions) == 3
    assert len(snapshot["options_transactions"]) == 4
    assert snapshot["portfolio_intelligence"]["capital_risk"] is not None
    assert len(snapshot["options_performance"]["lifecycles"]) == 2


def test_dashboard_upload_contracts(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    imports = data_dir / "imports"
    imports.mkdir(parents=True)
    _patch_data_dir(monkeypatch, data_dir)

    portfolio = tmp_path / "portfolio.xlsx"
    options = tmp_path / "options.xlsx"
    note = tmp_path / "nota.pdf"
    make_btg_portfolio(portfolio)
    make_options_transactions(options)
    make_brokerage_note(note)
    parsed_note = BrokerageNoteParser().parse_text(
        """NOTA DE CORRETAGEM\n34515456\nNr. nota\n17/09/2026\nData pregão\n1-BOVESPA C OPCAO DE COMPRA 10/26 ASAIJ970 ON 3000 0,94 2.820,00 D\n""",
        source_file="nota.pdf",
    )
    monkeypatch.setattr(server.BrokerageNoteParser, "parse", lambda self, path: parsed_note)

    client = TestClient(server.app)
    with portfolio.open("rb") as handle:
        response = client.post("/imports/portfolio", files={"file": ("portfolio.xlsx", handle, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert response.status_code == 200
    assert (imports / "portfolio.xlsx").exists()

    with options.open("rb") as handle:
        response = client.post("/imports/options", files={"file": ("options.xlsx", handle, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert response.status_code == 200
    assert (imports / "options_transactions.xlsx").exists()

    with note.open("rb") as handle:
        response = client.post("/imports/brokerage-notes", files={"file": ("nota.pdf", handle, "application/pdf")})
    assert response.status_code == 200
    assert response.json()["status"] == "processed"
    assert response.json()["parsed_count"] == 1
    assert response.json()["inserted_count"] == 1
    assert (imports / "brokerage_notes" / "nota.pdf").exists()
    assert len(OptionTransactionLedger(data_dir / "options.sqlite3").list_all()) == 1


def test_dashboard_upload_rejects_wrong_note_type(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    (data_dir / "imports").mkdir(parents=True)
    _patch_data_dir(monkeypatch, data_dir)
    client = TestClient(server.app)
    response = client.post(
        "/imports/brokerage-notes",
        files={"file": ("not-a-note.xlsx", b"bad", "application/octet-stream")},
    )
    assert response.status_code == 400


def test_frontend_boundary_has_no_option_business_inference() -> None:
    content = (Path(__file__).parents[1] / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")
    assert "infer_b3_option_type" not in content
    assert "/orchestrate" in content
    assert "/imports/portfolio" in content
    assert "/imports/options" in content
    assert "/imports/brokerage-notes" in content


def test_active_snapshots_use_existing_loaders(tmp_path) -> None:
    imports = tmp_path / "imports"
    imports.mkdir()
    make_btg_portfolio(imports / "portfolio.xlsx")
    make_options_transactions(imports / "options_transactions.xlsx")
    snapshots = load_active_snapshots(tmp_path)
    assert snapshots["portfolio_context"].quality_status == "VALIDATED"
    assert len(snapshots["options_transactions"]) == 4
