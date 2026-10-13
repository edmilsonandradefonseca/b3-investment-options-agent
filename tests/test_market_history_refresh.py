import importlib.util
from pathlib import Path

module_path = Path(__file__).resolve().parents[1] / "scripts" / "refresh_market_history.py"
spec = importlib.util.spec_from_file_location("refresh_market_history", module_path)
refresh_market_history = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(refresh_market_history)


def test_selected_tickers_uses_current_equity_universe_and_deduplicates(monkeypatch):
    monkeypatch.setattr(
        refresh_market_history,
        "_monitored_tickers",
        lambda: ("petr4", "PETR4", "PETR", "ITUB4", "", "BOVA11"),
    )

    assert refresh_market_history._selected_tickers() == ("PETR4", "ITUB4", "BOVA11")
