#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import urllib.request


BASE_URL = os.getenv("B3_API_URL", "http://127.0.0.1:8000").rstrip("/")


def _json_request(path: str, *, payload: dict | None = None) -> dict:
    data = None
    headers = {"Accept": "application/json"}
    method = "GET"
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
        method = "POST"
    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        result = json.loads(response.read().decode("utf-8"))
    if not isinstance(result, dict):
        raise RuntimeError(f"{path} returned a non-object response")
    return result


def main() -> None:
    health = _json_request("/health")
    runtime = health.get("runtime") or {}
    if health.get("status") != "ok":
        raise SystemExit("FAIL health is not ok")
    if not runtime.get("oplab_token_configured"):
        raise SystemExit("FAIL OPLAB_API_TOKEN is not configured in runtime")
    if not runtime.get("brapi_token_configured"):
        raise SystemExit("FAIL BRAPI_TOKEN is not configured in runtime")

    response = _json_request(
        "/orchestrate",
        payload={
            "task": (
                "UC-04: compare Comprar ação em VALE3 e Comprar ação em WEGE3. "
                "Mostre fatos canônicos e não invente ranking."
            ),
            "ticker": None,
            "context": {
                "workspace": "Strategy Lab",
                "selected_ticker": None,
                "comparison_assets": ["VALE3", "WEGE3"],
                "strategy_a": "Comprar ação",
                "strategy_b": "Comprar ação",
                "comparison_amount": 50000,
            },
        },
    )

    if response.get("status") != "COMPLETED":
        raise SystemExit(
            f"FAIL orchestrate status={response.get('status')} "
            f"error={response.get('error')}"
        )

    result = response.get("result") or {}
    fast_route = result.get("fast_route") or {}
    if fast_route.get("target") != "strategy_engine":
        raise SystemExit(
            f"FAIL expected strategy_engine, got {fast_route.get('target')}"
        )

    evidence = result.get("asset_evidence") or {}
    if set(evidence) != {"VALE3", "WEGE3"}:
        raise SystemExit(
            f"FAIL unexpected asset evidence keys={sorted(evidence)}"
        )

    limitations = [str(item) for item in (result.get("limitations") or [])]
    if any(
        "Fundamentals unavailable for WEGE3" in item
        for item in limitations
    ):
        raise SystemExit(
            "FAIL WEGE3 fundamentals are still unavailable after BRAPI fallback"
        )

    summary = {}
    for ticker in ("VALE3", "WEGE3"):
        pack = evidence[ticker]
        market = pack.get("market") or {}
        latest = market.get("latest") or {}
        fundamentals = pack.get("fundamentals") or {}
        metric_count = int(fundamentals.get("metric_count") or 0)
        if metric_count < 1:
            raise SystemExit(
                f"FAIL {ticker} returned zero fundamental metrics"
            )
        summary[ticker] = {
            "market_source": latest.get("source"),
            "latest_close": latest.get("close"),
            "history_count": market.get("history_count"),
            "fundamental_metric_count": metric_count,
            "quality_status": pack.get("quality_status"),
        }

    rendered = json.dumps(result, default=str)
    if "PETR4" in rendered:
        raise SystemExit(
            "FAIL unrelated PETR4 evidence leaked into VALE3/WEGE3 comparison"
        )

    print("PASS UC-04 REAL PROVIDERS")
    print(json.dumps({
        "route": fast_route.get("target"),
        "quality_status": result.get("quality_status"),
        "providers": summary,
        "limitations": limitations,
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
