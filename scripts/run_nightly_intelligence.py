#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from b3_agent.jobs.nightly_intelligence import NightlyIntelligenceJob


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", action="append", dest="tickers")
    parser.add_argument("--news-limit", type=int, default=8)
    args = parser.parse_args()
    result = NightlyIntelligenceJob(news_limit=args.news_limit).run(tickers=args.tickers)
    print(json.dumps({
        "ticker_count": result["ticker_count"],
        "completed": result["completed"],
        "skipped": result["skipped"],
        "deferred": result["deferred"],
        "failed": result["failed"],
        "deepseek_calls": result["deepseek_calls"],
        "as_of": result["as_of"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
