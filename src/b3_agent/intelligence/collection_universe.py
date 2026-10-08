from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from b3_agent.portfolio.snapshot import load_active_snapshots
from b3_agent.portfolio.instrument_identity import InstrumentIdentityResolver


_TICKER_RE = re.compile(r"^[A-Z]{4}[0-9]{1,2}$")


class CollectionUniverseStore:
    """Persist additional B3 equities monitored by scheduled jobs."""

    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)
        self.path = self.data_dir / "structured" / "collection_universe.json"

    @staticmethod
    def normalize_tickers(values: list[str] | tuple[str, ...]) -> list[str]:
        tickers: list[str] = []
        for value in values:
            ticker = str(value).strip().upper()
            if not ticker:
                continue
            if not _TICKER_RE.fullmatch(ticker):
                raise ValueError(f"invalid B3 equity ticker: {ticker}")
            if ticker not in tickers:
                tickers.append(ticker)
        return tickers

    def configured(self) -> dict[str, Any]:
        if self.path.exists():
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or not isinstance(payload.get("tickers"), list):
                raise ValueError("collection universe configuration has an invalid shape")
            values = self.normalize_tickers(payload["tickers"])
            return {
                "tickers": values,
                "updated_at": payload.get("updated_at"),
                "source": "admin",
            }

        legacy = [
            item.strip().upper()
            for item in os.getenv("B3_INTEL_WATCHLIST", "").split(",")
            if item.strip()
        ]
        return {
            "tickers": self.normalize_tickers(legacy),
            "updated_at": None,
            "source": "environment" if legacy else "default",
        }

    def save(self, values: list[str] | tuple[str, ...]) -> dict[str, Any]:
        tickers = self.normalize_tickers(values)
        payload = {
            "schema_version": 1,
            "tickers": tickers,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)
        return {"tickers": tickers, "updated_at": payload["updated_at"], "source": "admin"}

    def portfolio_tickers(self) -> list[str]:
        snapshots = load_active_snapshots(self.data_dir)
        portfolio = snapshots.get("portfolio_context")
        if portfolio is None:
            return []
        values: list[str] = []
        resolver = InstrumentIdentityResolver()
        for position in portfolio.positions:
            if position.instrument_type != "STOCK":
                continue
            value = position.ticker
            ticker = resolver.resolve(str(value))
            if not _TICKER_RE.fullmatch(ticker):
                logging.getLogger(__name__).warning(
                    "Unresolved portfolio identity excluded from collection universe: %s", value
                )
                continue
            if ticker and ticker not in values:
                values.append(ticker)
        return values

    def snapshot(self) -> dict[str, Any]:
        configured = self.configured()
        portfolio_tickers = self.portfolio_tickers()
        effective = list(portfolio_tickers)
        for ticker in configured["tickers"]:
            if ticker not in effective:
                effective.append(ticker)
        return {
            "configured_tickers": configured["tickers"],
            "portfolio_tickers": portfolio_tickers,
            "effective_tickers": effective,
            "updated_at": configured["updated_at"],
            "source": configured["source"],
        }

    def effective_tickers(self) -> tuple[str, ...]:
        return tuple(self.snapshot()["effective_tickers"])
