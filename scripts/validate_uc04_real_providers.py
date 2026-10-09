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
        "/options/current/WEGE3?option_type=PUT&limit=500"
    )
    option_rows = current_puts.get("options") or []
    if current_puts.get("source") != "oplab" or not option_rows:
        raise SystemExit("FAIL current OPLAB PUT quotes are unavailable")
    executable_row = next(
        (
            row
            for row in option_rows
            if isinstance((row.get("quote") or {}).get("bid"), (int, float))
            and (row.get("quote") or {}).get("bid") > 0
        ),
        None,
    )
    if executable_row is None:
        raise SystemExit(
            "FAIL no current WEGE3 PUT has executable bid > 0"
        )
    executable_contract = executable_row.get("contract") or {}
    executable_quote = executable_row.get("quote") or {}
    option_id = str(executable_contract.get("option_id") or "").upper().strip()
    if not option_id:
        raise SystemExit("FAIL executable PUT is missing option_id")

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

    sell_put_response = _json_request(
        "/orchestrate",
        payload={
            "task": (
                f"UC-04: compare Comprar ação em VALE3 e Vender PUT "
                f"{option_id} em WEGE3. Use cotações atuais OPLAB."
            ),
            "ticker": None,
            "context": {
                "workspace": "Strategy Lab",
                "selected_ticker": None,
                "comparison_assets": ["VALE3", "WEGE3"],
                "strategy_a": "Comprar ação",
                "strategy_b": "Vender PUT",
                "option_a": None,
                "option_b": option_id,
                "comparison_amount": 50000,
            },
        },
    )
    if sell_put_response.get("status") != "COMPLETED":
        raise SystemExit(
            f"FAIL SELL_PUT orchestrate status={sell_put_response.get('status')} "
            f"error={sell_put_response.get('error')}"
        )
    sell_put_result = sell_put_response.get("result") or {}
    sell_put_route = sell_put_result.get("fast_route") or {}
    if sell_put_route.get("target") != "strategy_engine":
        raise SystemExit(
            f"FAIL SELL_PUT expected strategy_engine, "
            f"got {sell_put_route.get('target')}"
        )
    option_evidence = sell_put_result.get("option_evidence") or {}
    selected = option_evidence.get(option_id) or {}
    selected_quote = selected.get("current_quote") or {}
    if not (
        selected.get("premium_basis") == "current_bid"
        and isinstance(selected_quote.get("bid"), (int, float))
        and selected_quote.get("bid") > 0
        and selected_quote.get("source") == "oplab"
    ):
        raise SystemExit(
            "FAIL SELL_PUT did not use the current executable OPLAB bid"
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
            "underlying": "WEGE3",
            "option_id": option_id,
            "bid": executable_quote.get("bid"),
            "ask": executable_quote.get("ask"),
            "last": executable_quote.get("last"),
            "mid": executable_quote.get("mid"),
            "as_of": executable_quote.get("observation_timestamp"),
            "source": executable_quote.get("source"),
        },
        "sell_put_e2e": {
            "route": sell_put_route.get("target"),
            "option_id": option_id,
            "premium_basis": selected.get("premium_basis"),
            "bid_used": selected_quote.get("bid"),
            "status": sell_put_response.get("status"),
        },
        "providers": summary,
        "limitations": limitations,
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
