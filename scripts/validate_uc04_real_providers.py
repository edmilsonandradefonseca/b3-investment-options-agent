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

    current_wege = _json_request("/market/current/WEGE3")
    current_quote = current_wege.get("quote") or {}
    if current_wege.get("source") != "oplab":
        raise SystemExit(
            f"FAIL WEGE3 current stock quote source={current_wege.get('source')}"
        )
    if not isinstance(current_quote.get("close"), (int, float)):
        raise SystemExit("FAIL WEGE3 current stock price is unavailable")

    current_puts = _json_request(
        "/options/current/VALE3?option_type=PUT&limit=5"
    )
    option_rows = current_puts.get("options") or []
    if current_puts.get("source") != "oplab" or not option_rows:
        raise SystemExit("FAIL current OPLAB PUT quotes are unavailable")
    first_option_quote = option_rows[0].get("quote") or {}
    if not any(
        isinstance(first_option_quote.get(field), (int, float))
        and first_option_quote.get(field) > 0
        for field in ("bid", "ask", "last", "mid")
    ):
        raise SystemExit("FAIL current option quote has no usable market price")

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
        current = market.get("current_quote") or {}
        history_latest = market.get("history_latest") or market.get("latest") or {}
        fundamentals = pack.get("fundamentals") or {}
        metric_count = int(fundamentals.get("metric_count") or 0)
        if metric_count < 1:
            raise SystemExit(
                f"FAIL {ticker} returned zero fundamental metrics"
            )
        summary[ticker] = {
            "current_price_source": current.get("source"),
            "current_price": current.get("close"),
            "historical_close": history_latest.get("close"),
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
        "current_stock_quote": {
            "ticker": "WEGE3",
            "source": current_wege.get("source"),
            "price": current_quote.get("close"),
            "as_of": current_wege.get("as_of"),
        },
        "current_option_quote": {
            "underlying": "VALE3",
            "option_id": (option_rows[0].get("contract") or {}).get("option_id"),
            "bid": first_option_quote.get("bid"),
            "ask": first_option_quote.get("ask"),
            "last": first_option_quote.get("last"),
            "mid": first_option_quote.get("mid"),
            "as_of": first_option_quote.get("observation_timestamp"),
            "source": first_option_quote.get("source"),
        },
        "providers": summary,
        "limitations": limitations,
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
