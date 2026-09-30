#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from b3_agent.jobs.continuous_intelligence import ContinuousIntelligenceJob


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--tickers",
        default="",
        help="Optional comma-separated monitored tickers; portfolio/watchlist used by default.",
    )
    args = parser.parse_args()
    tickers = [
        item.upper().strip()
        for item in args.tickers.split(",")
        if item.strip()
    ]
    result = ContinuousIntelligenceJob().run(
        monitored_tickers=tickers or None,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
