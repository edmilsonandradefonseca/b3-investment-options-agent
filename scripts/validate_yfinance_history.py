#!/usr/bin/env python3
"""Read-only Yahoo daily-history pilot against the existing local market archive.

This script never writes downloaded rows to the project or runtime data stores.
It emits aggregate coverage/difference metadata only.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import json
import math
from pathlib import Path
import statistics
from time import monotonic


def _day(value) -> date:
    if hasattr(value, "date"):
        result = value.date()
        return result if isinstance(result, date) else date.fromisoformat(str(result))
    return date.fromisoformat(str(value)[:10])


def _finite(value) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _compare(ticker: str, frame, local_rows: list) -> dict:
    yahoo: dict[date, dict] = {}
    for index, row in frame.iterrows():
        day = _day(index)
        close = _finite(row.get("Close"))
        if close is None:
            continue
        yahoo[day] = {
            key.lower(): _finite(row.get(key))
            for key in ("Open", "High", "Low", "Close", "Volume")
        }

    local: dict[date, dict] = {}
    for row in local_rows:
        day = _day(row.observation_timestamp)
        if row.close is None:
            continue
        local[day] = {
            "open": _finite(row.open),
            "high": _finite(row.high),
            "low": _finite(row.low),
            "close": _finite(row.close),
            "volume": _finite(row.volume),
            "source": row.source,
        }

    overlap = sorted(set(yahoo) & set(local))
    close_abs_pct: list[float] = []
    ohlc_matches = 0
    ohlc_compared = 0
    volume_matches = 0
    volume_compared = 0
    for day in overlap:
        yc, lc = yahoo[day]["close"], local[day]["close"]
        if yc is not None and lc is not None and lc != 0:
            close_abs_pct.append(abs(yc - lc) / abs(lc) * 100)
        bar_pairs = [
            (yahoo[day][field], local[day][field])
            for field in ("open", "high", "low", "close")
        ]
        for left, right in bar_pairs:
            if left is not None and right is not None:
                ohlc_compared += 1
                if math.isclose(left, right, rel_tol=0, abs_tol=0.011):
                    ohlc_matches += 1
        yv, lv = yahoo[day]["volume"], local[day]["volume"]
        if yv is not None and lv is not None:
            volume_compared += 1
            if math.isclose(yv, lv, rel_tol=0, abs_tol=1):
                volume_matches += 1

    latest_yahoo = max(yahoo) if yahoo else None
    latest_local = max(local) if local else None
    actions = {}
    for column in ("Dividends", "Stock Splits"):
        if column in frame.columns:
            actions[column.lower().replace(" ", "_")] = int(
                sum(
                    1
                    for value in frame[column].tolist()
                    if (_finite(value) or 0) != 0
                )
            )
    return {
        "ticker": ticker,
        "status": "READ_OK" if yahoo else "EMPTY",
        "yahoo_row_count": len(yahoo),
        "yahoo_first_date": min(yahoo).isoformat() if yahoo else None,
        "yahoo_latest_date": latest_yahoo.isoformat() if latest_yahoo else None,
        "yahoo_latest_calendar_age_days": (
            (datetime.now(timezone.utc).date() - latest_yahoo).days
            if latest_yahoo else None
        ),
        "local_row_count_1y": len(local),
        "local_latest_date": latest_local.isoformat() if latest_local else None,
        "overlap_day_count": len(overlap),
        "close_abs_pct_median": (
            round(statistics.median(close_abs_pct), 6) if close_abs_pct else None
        ),
        "close_abs_pct_max": round(max(close_abs_pct), 6) if close_abs_pct else None,
        "ohlc_within_0_011_match_pct": (
            round(ohlc_matches / ohlc_compared * 100, 3)
            if ohlc_compared else None
        ),
        "volume_within_one_share_match_pct": (
            round(volume_matches / volume_compared * 100, 3)
            if volume_compared else None
        ),
        "corporate_action_row_counts": actions,
        "local_sources": sorted({str(item["source"]) for item in local.values()}),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--market-root", type=Path, required=True)
    parser.add_argument(
        "--tickers",
        nargs="+",
        default=["PETR4", "VALE3", "ITUB4", "BBDC4", "WEGE3"],
    )
    parser.add_argument("--days", type=int, default=365)
    args = parser.parse_args()

    import yfinance as yf
    from b3_agent.repositories.market_data import MarketDataRepository

    repo = MarketDataRepository(args.market_root)
    cutoff = datetime.now(timezone.utc).date() - timedelta(days=args.days)
    print(json.dumps({
        "pilot": "YAHOO_DAILY_HISTORY_READ_ONLY",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "yfinance_version": getattr(yf, "__version__", "UNKNOWN"),
        "tickers": args.tickers,
        "period_days": args.days,
        "auto_adjust": False,
        "actions": True,
        "write_to_runtime_store": False,
    }, sort_keys=True), flush=True)

    successes = 0
    for raw_ticker in args.tickers:
        ticker = raw_ticker.upper().strip()
        started = monotonic()
        try:
            rows = [
                row for row in repo.read(ticker)
                if _day(row.observation_timestamp) >= cutoff
            ]
            frame = yf.Ticker(f"{ticker}.SA").history(
                period=f"{max(1, math.ceil(args.days / 365))}y",
                interval="1d",
                auto_adjust=False,
                actions=True,
                timeout=10,
                raise_errors=True,
            )
            result = _compare(ticker, frame, rows)
            result["elapsed_ms"] = round((monotonic() - started) * 1000, 1)
            if result["status"] == "READ_OK":
                successes += 1
        except Exception as exc:
            result = {
                "ticker": ticker,
                "status": "ERROR",
                "error_type": type(exc).__name__,
                "elapsed_ms": round((monotonic() - started) * 1000, 1),
            }
        print(json.dumps(result, sort_keys=True), flush=True)

    print(f"YAHOO_PILOT_SUCCESSFUL_TICKERS={successes}/{len(args.tickers)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
