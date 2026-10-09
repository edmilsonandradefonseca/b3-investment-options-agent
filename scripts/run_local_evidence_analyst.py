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

from b3_agent.jobs.local_evidence_analyst import LocalEvidenceAnalystJob


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--max-batches", type=int, default=20)
    parser.add_argument("--max-seconds", type=float, default=1800)
    args = parser.parse_args()

    if args.limit < 1 or args.max_batches < 1 or args.max_seconds <= 0:
        parser.error("limit, max-batches and max-seconds must be positive")
    result = LocalEvidenceAnalystJob().run_until_idle(limit=args.limit, max_batches=args.max_batches,
                                                     max_seconds=args.max_seconds)
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return 0 if result['failed'] == result['degraded'] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
