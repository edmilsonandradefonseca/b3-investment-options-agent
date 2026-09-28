#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import asdict

from b3_agent.routing import FastRouter


def main() -> int:
    router = FastRouter()
    cases = [
        {"text": "qual o preço de PETR4?"},
        {"text": "qual o delta e theta da minha PUT PETR4?"},
        {"text": "rode stress com IBOV -10%"},
        {"text": "compare comprar PETR4 com vender uma PUT"},
        {"text": "o que você acha disso?"},
        {"source": "scheduler", "task_type": "b3.news.nightly"},
    ]
    print("===== B3 FAST ROUTER V1 SMOKE =====")
    for case in cases:
        decision = router.route(**case)
        row = asdict(decision)
        row["target"] = decision.target.value
        row["match"] = decision.match.value
        print(json.dumps(row, ensure_ascii=False, sort_keys=True))
    print("===== B3 FAST ROUTER V1 SMOKE PASSED =====")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
