from pathlib import Path

from b3_agent.portfolio import snapshot


def test_load_active_snapshots_uses_current_replacement_files(monkeypatch, tmp_path: Path) -> None:
    imports = tmp_path / "imports"
    imports.mkdir()
    (imports / "portfolio.xlsx").write_bytes(b"portfolio")
    (imports / "options_transactions.xlsx").write_bytes(b"options")

    portfolio = object()
    transactions = object()

    monkeypatch.setattr(snapshot.BtgRendaVariavelLoader, "load", lambda self, path: portfolio)
    monkeypatch.setattr(snapshot.OptionsTransactionLoader, "load", lambda self, path: (transactions,))
    monkeypatch.setattr(snapshot, "asdict", lambda item: {"transaction": "current"})

    result = snapshot.load_active_snapshots(tmp_path)

    assert result["portfolio_context"] is portfolio
    assert result["options_transactions"] == ({"transaction": "current"},)


def test_load_active_snapshots_ignores_missing_snapshot(tmp_path: Path) -> None:
    result = snapshot.load_active_snapshots(tmp_path)

    assert result == {}
