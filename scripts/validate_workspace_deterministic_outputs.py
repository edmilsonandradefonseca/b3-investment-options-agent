#!/usr/bin/env python3
"""Compare deterministic workspace outputs and direct Market Intelligence APIs.

Full payloads stay in a mode-0600 file on the Ubuntu runner host. Only response
status, latency, and non-sensitive structural counts are written to Actions logs.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

MAX_RESPONSE_BYTES = 20 * 1024 * 1024


def call_json(url: str, payload: dict[str, Any] | None, timeout: float) -> dict[str, Any]:
    headers = {"Accept": "application/json"}
    data = None
    method = "GET"
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
        method = "POST"
    started = time.monotonic()
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            status = int(response.status)
    except HTTPError as exc:
        status = int(exc.code)
        raw = exc.read(MAX_RESPONSE_BYTES + 1)
    except (URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", None)
        return {
            "http_status": None,
            "elapsed_ms": round((time.monotonic() - started) * 1000, 1),
            "response_bytes": 0,
            "transport_error_type": type(reason if reason is not None else exc).__name__,
            "response": None,
        }
    result: Any
    if len(raw) > MAX_RESPONSE_BYTES:
        result = None
        transport_error = "RESPONSE_TOO_LARGE"
    else:
        try:
            result = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            result = {"_raw_text": raw.decode("utf-8", errors="replace")}
        transport_error = None
    return {
        "http_status": status,
        "elapsed_ms": round((time.monotonic() - started) * 1000, 1),
        "response_bytes": len(raw),
        "transport_error_type": transport_error,
        "response": result,
    }


def summary(name: str, response: Any) -> dict[str, Any]:
    if not isinstance(response, dict):
        return {"response_type": type(response).__name__}
    if name.startswith("orchestrate_"):
        result = response.get("result")
        result = result if isinstance(result, dict) else {}
        context = result.get("deterministic_context")
        context = context if isinstance(context, dict) else {}
        workspace_result = context.get("workspace_result")
        workspace_result = workspace_result if isinstance(workspace_result, dict) else {}
        market = result.get("research_context")
        market = market if isinstance(market, dict) else {}
        tickers = market.get("tickers")
        tickers = tickers if isinstance(tickers, dict) else {}
        opportunity = workspace_result.get("opportunity_set")
        opportunity = opportunity if isinstance(opportunity, dict) else {}
        strategies = workspace_result.get("strategy_comparison")
        strategies = strategies if isinstance(strategies, dict) else {}
        return {
            "api_status": response.get("status"),
            "error_present": bool(response.get("error")),
            "result_keys": sorted(str(key) for key in result)[:80],
            "workspace_result_keys": sorted(str(key) for key in workspace_result)[:80],
            "opportunity_candidate_count": len(opportunity.get("candidates", [])) if isinstance(opportunity.get("candidates"), list) else None,
            "opportunity_ranking_status": workspace_result.get("opportunity_ranking_status"),
            "strategy_result_keys": sorted(str(key) for key in strategies)[:50],
            "ticker_context_count": len(tickers),
            "stored_research_ticker_count": len(result.get("stored_research", {})) if isinstance(result.get("stored_research"), dict) else None,
            "derived_synthesis_status": result.get("derived_synthesis_status"),
            "telemetry_stage_names": sorted(str(key) for key in result.get("telemetry", {}).get("stages", {})) if isinstance(result.get("telemetry"), dict) and isinstance(result.get("telemetry", {}).get("stages"), dict) else [],
            "source_count": len(response.get("sources", [])) if isinstance(response.get("sources"), list) else None,
        }
    if name == "market_live":
        market = response.get("market")
        market = market if isinstance(market, dict) else {}
        quant = market.get("quant")
        quant = quant if isinstance(quant, dict) else {}
        return {
            "ticker": response.get("ticker"),
            "history_count": market.get("history_count"),
            "current_quote_present": isinstance(market.get("current_quote"), dict),
            "latest_quote_present": isinstance(market.get("latest"), dict),
            "quant_fields": sorted(str(key) for key in quant),
            "source_count": len(response.get("source_refs", [])) if isinstance(response.get("source_refs"), list) else None,
        }
    if name in {"market_stored_research", "market_fresh_news"}:
        return {
            "ticker": response.get("ticker"),
            "event_count": len(response.get("events", [])) if isinstance(response.get("events"), list) else None,
            "source_count": len(response.get("source_refs", [])) if isinstance(response.get("source_refs"), list) else None,
            "excluded_future_count": response.get("excluded_future_count"),
        }
    detail = response.get("detail")
    detail_text = str(detail).casefold() if detail is not None else ""
    category = (
        "OPLAB_PROVIDER" if "oplab" in detail_text else
        "BRAPI_PROVIDER" if "brapi" in detail_text else
        "OPENCLAW_OR_LLM" if "openclaw" in detail_text or "llm" in detail_text else
        "RESEARCH_PROVIDER" if "research" in detail_text or "searx" in detail_text or "news" in detail_text else
        "API_ERROR" if detail is not None else None
    )
    return {"error_present": detail is not None or bool(response.get("error")), "error_category": category}


def write_report(directory: Path, report: dict[str, Any]) -> Path:
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        directory.chmod(0o700)
    except OSError:
        pass
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = directory / f"b3-deterministic-workspaces-{stamp}.json"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.getenv("B3_BASE_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--timeout-seconds", type=float, default=75)
    parser.add_argument("--report-dir", default=os.getenv("B3_REPORT_DIR", str(Path.home() / ".local/share/b3-investment-options-agent/live-validation")))
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    common = {"research_mode": "stored_only", "option_filter": None, "horizon": "1M", "analysis_mode": "deterministic"}
    cases = [
        ("opportunities_petr4", {
            "task": "UC-03: analise PETR4 sob demanda, elegibilidade, risco, evidências e ranking canônico disponível.",
            "ticker": "PETR4",
            "context": {**common, "workspace": "Opportunities", "selected_ticker": "PETR4", "asset_view": False},
        }),
        ("market_intelligence_vale3", {
            "task": "UC-05/06/10: analise VALE3 integrando preço atual, histórico, fundamentos, regime/fatores disponíveis, notícias/eventos e inteligência derivada B3/João. Preserve fatos canônicos, as_of, riscos, contradições, limitações e fontes.",
            "ticker": "VALE3",
            "context": {**common, "workspace": "Market Intelligence", "selected_ticker": "VALE3", "asset_view": True},
        }),
        ("strategy_lab_stock_buy_comparison", {
            "task": "UC-04: compare Comprar ação em ITUB4 e Comprar ação em BBDC4. Use cotações atuais OPLAB separadas do histórico. Mostre cenários, premissas e riscos canônicos; não atribua probabilidade aos choques.",
            "ticker": None,
            "context": {
                **common, "workspace": "Strategy Lab", "selected_ticker": None, "asset_view": False,
                "comparison_assets": ["ITUB4", "BBDC4"], "strategy_a": "Comprar ação", "strategy_b": "Comprar ação",
                "option_a": None, "option_b": None, "comparison_amount": None, "scenario_horizon": None,
                "scenario_shocks_pct": None, "scenario_objective": "COMPARE_ONLY",
            },
        }),
    ]
    report: dict[str, Any] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base,
        "analysis_mode": "deterministic",
        "privacy": "Full responses are local mode-0600 only; Actions logs contain metadata and structural counts.",
        "calls": [],
    }
    jobs: list[tuple[str, str, dict[str, Any] | None]] = [
        ("health", f"{base}/health", None),
        ("version", f"{base}/version", None),
    ]
    jobs.extend((f"orchestrate_{case_id}", f"{base}/orchestrate", payload) for case_id, payload in cases)
    market = "VALE3"
    jobs.extend([
        ("market_live", f"{base}/analysis/live/{market}", None),
        ("market_stored_research", f"{base}/intelligence/research-context?ticker={market}&limit=8", None),
        ("market_fresh_news", f"{base}/research/news/{market}?limit=20", None),
    ])
    failures = 0
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {
            pool.submit(call_json, url, payload, min(args.timeout_seconds, 15) if name in {"health", "version"} else args.timeout_seconds): name
            for name, url, payload in jobs
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                result = {"http_status": None, "elapsed_ms": None, "transport_error_type": type(exc).__name__, "response": None, "response_bytes": 0}
            entry = {"name": name, **result, "summary": summary(name, result.get("response"))}
            report["calls"].append(entry)
            status = result.get("http_status")
            if result.get("transport_error_type") or not isinstance(status, int) or status >= 400:
                failures += 1
            print(
                f"CALL {name} http={status} elapsed_ms={result.get('elapsed_ms')} "
                f"bytes={result.get('response_bytes')} transport_error={result.get('transport_error_type')} "
                f"summary={json.dumps(entry['summary'], ensure_ascii=False, separators=(',', ':'))}",
                flush=True,
            )
    report["calls"].sort(key=lambda item: item["name"])
    report_path = write_report(Path(args.report_dir).expanduser(), report)
    print(f"PRIVATE_REPORT={report_path}", flush=True)
    print("REPORT_CONTENT=not printed; no portfolio values or response body are logged.", flush=True)
    print(f"VALIDATION_FAILURE_COUNT={failures}", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
