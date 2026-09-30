#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from b3_agent.config import settings
from b3_agent.intelligence.issuer_registry import IssuerRegistry


TICKER_RE = re.compile(r"^[A-Z]{4}\d{1,2}$")


def main() -> int:
    now = datetime.now(ZoneInfo(settings.timezone))
    registry = IssuerRegistry()
    sync = registry.sync_from_cvm(year=now.year, as_of=now.date())

    invalid_rows: list[dict[str, str]] = []
    with sqlite3.connect(registry.path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT instrument_id, ticker, issuer_id, exchange_name, reference_date
            FROM securities
            WHERE source = 'CVM_FCA_OPEN_DATA'
            ORDER BY ticker, issuer_id
            """
        ).fetchall()
        for row in rows:
            ticker = str(row["ticker"] or "").strip().upper()
            if TICKER_RE.fullmatch(ticker) is None:
                invalid_rows.append(
                    {
                        "instrument_id": str(row["instrument_id"]),
                        "ticker": ticker,
                        "issuer_id": str(row["issuer_id"]),
                        "exchange_name": str(row["exchange_name"] or ""),
                        "reference_date": str(row["reference_date"] or ""),
                    }
                )

    representative = {}
    for ticker in ("PETR4", "XPBR31"):
        issuer = registry.resolve_issuer_by_ticker(ticker, as_of=now.date())
        representative[ticker] = issuer.issuer_id if issuer else None

    result = {
        "V4_3_IDENTITY_ACCEPTANCE": "PASS" if not invalid_rows else "FAIL",
        "as_of": now.isoformat(),
        "sync": {
            "fca_year": sync["fca_year"],
            "issuer_count": sync["issuer_count"],
            "security_count": sync["security_count"],
            "active_security_count": sync["active_security_count"],
            "unmatched_security_count": sync["unmatched_security_count"],
            "invalid_security_count": sync.get("invalid_security_count", 0),
            "purged_invalid_security_count": sync.get(
                "purged_invalid_security_count", 0
            ),
        },
        "invalid_registry_rows": invalid_rows,
        "representative_resolution": representative,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not invalid_rows else 2


if __name__ == "__main__":
    raise SystemExit(main())
