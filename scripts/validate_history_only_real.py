#!/usr/bin/env python3
"""Read-only Ubuntu probe for the chart/history-only live-provider path."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from time import monotonic

from b3_agent.orchestration.live_providers import LiveProviderService


def main() -> int:
    tickers = ("PETR4", "ITUB4", "BBDC4", "WEGE3")
    failures = 0
    for ticker in tickers:
        started = monotonic()
        try:
            snapshot = LiveProviderService().load(
                ticker,
                as_of=datetime.now(timezone.utc),
                include_current_quote=False,
                include_options=False,
            )
            latest = max(
                snapshot.market_records,
                key=lambda record: record.observation_timestamp,
            )
            payload = {
                "ticker": ticker,
                "status": "READ_OK",
                "elapsed_ms": round((monotonic() - started) * 1000, 1),
                "history_count": len(snapshot.market_records),
                "history_latest_date": latest.observation_timestamp.date().isoformat(),
                "history_sources": sorted({record.source for record in snapshot.market_records}),
                "current_quote_requested": False,
                "current_quote_returned": snapshot.current_stock_quote is not None,
                "option_chain_requested": False,
                "option_contract_count": len(snapshot.option_contracts),
                "source_refs": list(snapshot.source_refs),
            }
            if not snapshot.market_records:
                failures += 1
        except Exception as exc:
            failures += 1
            payload = {
                "ticker": ticker,
                "status": "ERROR",
                "error_type": type(exc).__name__,
                "elapsed_ms": round((monotonic() - started) * 1000, 1),
            }
        print(json.dumps(payload, sort_keys=True), flush=True)

    print(f"HISTORY_ONLY_FAILURE_COUNT={failures}", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
