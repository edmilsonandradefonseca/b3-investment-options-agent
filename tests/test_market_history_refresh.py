from scripts import refresh_market_history


def test_selected_tickers_uses_current_equity_universe_and_deduplicates(monkeypatch):
    monkeypatch.setattr(
        refresh_market_history,
        "_monitored_tickers",
        lambda: ("petr4", "PETR4", "PETR", "ITUB4", "", "BOVA11"),
    )

    assert refresh_market_history._selected_tickers() == ("PETR4", "ITUB4", "BOVA11")
