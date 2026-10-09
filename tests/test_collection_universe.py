from __future__ import annotations

import json

import pytest

from b3_agent.intelligence.collection_universe import CollectionUniverseStore


def test_store_deduplicates_and_normalizes_b3_tickers(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "b3_agent.intelligence.collection_universe.load_active_snapshots",
        lambda _data_dir: {},
    )
    store = CollectionUniverseStore(tmp_path)

    saved = store.save(["vale3", "ITUB4", "VALE3"])

    assert saved["tickers"] == ["VALE3", "ITUB4"]
    assert saved["source"] == "admin"
    assert store.snapshot()["effective_tickers"] == ["VALE3", "ITUB4"]
    persisted = json.loads(store.path.read_text(encoding="utf-8"))
    assert persisted["schema_version"] == 1
    assert persisted["tickers"] == ["VALE3", "ITUB4"]


def test_invalid_ticker_is_rejected_without_overwriting_existing_config(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "b3_agent.intelligence.collection_universe.load_active_snapshots",
        lambda _data_dir: {},
    )
    store = CollectionUniverseStore(tmp_path)
    store.save(["VALE3"])

    with pytest.raises(ValueError, match="invalid B3 equity ticker"):
        store.save(["VALE3", "BTC"])

    assert store.configured()["tickers"] == ["VALE3"]


def test_saved_empty_universe_overrides_legacy_environment(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("B3_INTEL_WATCHLIST", "VALE3,ITUB4")
    monkeypatch.setattr(
        "b3_agent.intelligence.collection_universe.load_active_snapshots",
        lambda _data_dir: {},
    )
    store = CollectionUniverseStore(tmp_path)

    assert store.configured()["source"] == "environment"
    store.save([])

    assert store.configured()["source"] == "admin"
    assert store.effective_tickers() == ()


def test_portfolio_assets_remain_in_effective_collection_universe(tmp_path, monkeypatch) -> None:
    class Position:
        ticker = "PETR4"
        instrument_type = "STOCK"
        underlying_ticker = None

    class Portfolio:
        positions = [Position()]

    monkeypatch.setattr(
        "b3_agent.intelligence.collection_universe.load_active_snapshots",
        lambda _data_dir: {"portfolio_context": Portfolio()},
    )
    store = CollectionUniverseStore(tmp_path)
    store.save(["VALE3"])

    snapshot = store.snapshot()
    assert snapshot["portfolio_tickers"] == ["PETR4"]
    assert snapshot["effective_tickers"] == ["PETR4", "VALE3"]


def test_options_never_expand_stock_collection_universe(tmp_path, monkeypatch):
    from types import SimpleNamespace
    positions = [
        SimpleNamespace(ticker="PETR4", instrument_type="STOCK", underlying_ticker=None),
        SimpleNamespace(ticker="BBDCJ213", instrument_type="OPTION", underlying_ticker="BRADPN"),
        SimpleNamespace(ticker="VALEV650", instrument_type="OPTION", underlying_ticker="VALEON"),
        SimpleNamespace(ticker="PETRJ360", instrument_type="OPTION", underlying_ticker="PETRPN"),
    ]
    monkeypatch.setattr(
        "b3_agent.intelligence.collection_universe.load_active_snapshots",
        lambda _: {"portfolio_context": SimpleNamespace(positions=positions)},
    )
    store = CollectionUniverseStore(tmp_path)
    store.save(["ITUB4", "PETR4"])
    assert store.effective_tickers() == ("PETR4", "ITUB4")
    assert len(positions) == 4
    assert positions[1].underlying_ticker == "BRADPN"
    store.save(["BBDC4"])
    assert store.effective_tickers() == ("PETR4", "BBDC4")


def test_explicit_exclusions_override_holdings_and_survive_watchlist_save(tmp_path, monkeypatch):
    from types import SimpleNamespace
    positions = [SimpleNamespace(ticker=t, instrument_type="STOCK") for t in ("AXIA17", "AXIA7", "CURY3")]
    monkeypatch.setattr(
        "b3_agent.intelligence.collection_universe.load_active_snapshots",
        lambda _: {"portfolio_context": SimpleNamespace(positions=positions)},
    )
    store = CollectionUniverseStore(tmp_path)
    store.save(["VALE3", "CURY3", "AXIA17"], excluded_tickers=["AXIA17", "AXIA7"])
    assert store.effective_tickers() == ("CURY3", "VALE3")
    store.save(["SBSP3"])
    assert store.effective_tickers() == ("CURY3", "SBSP3")
    assert len(positions) == 3
