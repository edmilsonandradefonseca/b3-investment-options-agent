#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from b3_agent.jobs.cvm_reconciliation import CvmReconciliationJob


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=None)
    args = parser.parse_args()
    result = CvmReconciliationJob().run(year=args.year)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
