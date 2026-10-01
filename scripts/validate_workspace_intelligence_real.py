#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request


BASE_URL = os.getenv("B3_API_URL", "http://127.0.0.1:8000").rstrip("/")
TIMEOUT = float(os.getenv("B3_WORKSPACE_VALIDATION_TIMEOUT_SECONDS", "180"))
STARTUP_TIMEOUT = float(os.getenv("B3_WORKSPACE_STARTUP_TIMEOUT_SECONDS", "45"))


def wait_for_runtime() -> float:
    started = time.monotonic()
    deadline = started + STARTUP_TIMEOUT
    last_error = "not attempted"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(
                f"{BASE_URL}/health",
                timeout=2.0,
            ) as response:
                if 200 <= response.status < 300:
                    return time.monotonic() - started
                last_error = f"HTTP {response.status}"
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = str(exc)
        time.sleep(0.5)
    raise SystemExit(
        f"FAIL runtime did not become healthy within {STARTUP_TIMEOUT:.0f}s: "
        f"{last_error}. Check: sudo systemctl status b3-runtime.service "
        "--no-pager -l && sudo journalctl -u b3-runtime.service -n 80 --no-pager"
    )


def post_orchestrate(payload: dict) -> tuple[dict, float]:
    request = urllib.request.Request(
        f"{BASE_URL}/orchestrate",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    started = time.monotonic()
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        body = json.loads(response.read().decode("utf-8"))
    elapsed = time.monotonic() - started
    if not isinstance(body, dict):
        raise RuntimeError("orchestrate returned a non-object response")
    return body, elapsed


def require_intelligence(
    name: str,
    response: dict,
    *,
    expected_tickers: tuple[str, ...] = (),
    require_fast_strategy: bool = False,
) -> dict:
    if response.get("error"):
        raise SystemExit(f"FAIL {name}: {response['error']}")

    result = response.get("result") or {}
    workspace = result.get("workspace_intelligence") or {}
    if not workspace:
        raise SystemExit(f"FAIL {name}: workspace_intelligence missing")

    derived = workspace.get("derived_intelligence") or {}
    joao_memory = derived.get("joao_memory_context") or {}
    memory_ready = (
        joao_memory.get("source") == "joao-memory-api"
        and joao_memory.get("status") != "UNAVAILABLE"
    )

    joao = derived.get("joao_resolve") or {}
    if joao.get("status") != "READY":
        raise SystemExit(
            f"FAIL {name}: João Resolve status={joao.get('status')} "
            f"error={joao.get('error')}"
        )

    for key in (
        "market_agent_analysis",
        "portfolio_agent_analysis",
        "options_agent_analysis",
        "synthesis",
        "proposal",
    ):
        if not isinstance(result.get(key), dict):
            raise SystemExit(f"FAIL {name}: B3 senior output {key} missing")

    if require_fast_strategy:
        fast = result.get("fast_route") or {}
        if fast.get("target") != "strategy_engine":
            raise SystemExit(
                f"FAIL {name}: deterministic strategy route={fast.get('target')}"
            )
        if not result.get("asset_evidence"):
            raise SystemExit(f"FAIL {name}: deterministic asset evidence missing")

    market = workspace.get("market_context") or {}
    by_ticker = market.get("tickers") or {}
    asset_checks: dict[str, dict] = {}
    for ticker in expected_tickers:
        ticker_market = by_ticker.get(ticker) or {}
        current = ticker_market.get("current_quote") or {}
        if current.get("source") != "oplab":
            raise SystemExit(
                f"FAIL {name}: {ticker} current quote is not from OPLAB"
            )
        if not isinstance(current.get("close"), (int, float)):
            raise SystemExit(
                f"FAIL {name}: {ticker} current OPLAB price missing"
            )

        pack = ticker_market.get("asset_evidence") or {}
        if not isinstance(pack, dict) or not pack:
            raise SystemExit(
                f"FAIL {name}: deterministic asset_evidence missing for {ticker}"
            )
        pack_market = pack.get("market") or {}
        quant = pack.get("quant") or {}
        fundamentals = pack.get("fundamentals") or {}
        if int(pack_market.get("history_count") or 0) < 1:
            raise SystemExit(
                f"FAIL {name}: deterministic history missing for {ticker}"
            )
        if not isinstance(quant, dict) or not quant:
            raise SystemExit(
                f"FAIL {name}: deterministic quant evidence missing for {ticker}"
            )
        if int(fundamentals.get("metric_count") or 0) < 1:
            raise SystemExit(
                f"FAIL {name}: deterministic fundamentals missing for {ticker}"
            )
        asset_checks[ticker] = {
            "current_price": current.get("close"),
            "history_count": pack_market.get("history_count"),
            "fundamental_metric_count": fundamentals.get("metric_count"),
            "quality_status": pack.get("quality_status"),
        }

    local = derived.get("b3_local_evidence_analyst") or {}
    local_status = {
        ticker: (item or {}).get("status")
        for ticker, item in local.items()
        if isinstance(item, dict)
    }

    return {
        "status": response.get("status"),
        "joao": joao.get("status"),
        "joao_memory": {
            "status": "READY" if memory_ready else "UNAVAILABLE",
            "source": joao_memory.get("source"),
            "memory_count": len(joao_memory.get("memories") or []),
            "relation_count": len(joao_memory.get("relations") or []),
            "error": joao_memory.get("error"),
        },
        "b3_agents": {
            "market": bool(result.get("market_agent_analysis")),
            "portfolio": bool(result.get("portfolio_agent_analysis")),
            "options": bool(result.get("options_agent_analysis")),
            "synthesis": bool(result.get("synthesis")),
            "proposal": bool(result.get("proposal")),
        },
        "sources": len(response.get("sources") or []),
        "asset_evidence": asset_checks,
        "b3_local_intelligence": local_status,
        "limitations": workspace.get("limitations") or [],
        "market": market,
        "result": result,
    }


def main() -> None:
    report: dict[str, dict] = {}

    print("[0/3] Aguardando b3-runtime ficar saudável...", flush=True)
    startup_seconds = wait_for_runtime()
    print(f"[0/3] b3-runtime saudável em {startup_seconds:.1f}s", flush=True)

    print("[1/3] Strategy Lab: validando B3 + João + mercado...", flush=True)
    strategy_response, strategy_seconds = post_orchestrate(
        {
            "task": (
                "UC-04: compare Comprar ação em VALE3 e Comprar ação em WEGE3. "
                "Integre fatos canônicos, mercado atual, inteligência B3/DeepSeek "
                "e perspectiva João Resolve. Não invente ranking."
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
        }
    )
    strategy = require_intelligence(
        "Strategy Lab",
        strategy_response,
        expected_tickers=("VALE3", "WEGE3"),
        require_fast_strategy=True,
    )
    report["strategy_lab"] = {
        "seconds": round(strategy_seconds, 2),
        "status": strategy["status"],
        "joao": strategy["joao"],
        "joao_memory": strategy["joao_memory"],
        "b3_agents": strategy["b3_agents"],
        "sources": strategy["sources"],
        "asset_evidence": strategy["asset_evidence"],
        "b3_local_intelligence": strategy["b3_local_intelligence"],
        "limitations": strategy["limitations"],
    }

    print(f"[1/3] Strategy Lab OK em {strategy_seconds:.1f}s", flush=True)
    print("[2/3] Market Intelligence: validando macro + pesquisa + agentes...", flush=True)
    market_response, market_seconds = post_orchestrate(
        {
            "task": (
                "UC-05/06/10: produza inteligência de mercado integrando macro, "
                "eventos/notícias atuais, agentes B3, DeepSeek disponível e João "
                "Resolve; preserve fontes, incertezas e autoridade determinística."
            ),
            "ticker": None,
            "context": {
                "workspace": "Market Intelligence",
                "selected_ticker": None,
                "asset_view": False,
            },
        }
    )
    market = require_intelligence("Market Intelligence", market_response)
    macro = market["market"].get("macro") or {}
    if not macro:
        raise SystemExit("FAIL Market Intelligence: macro context missing")
    report["market_intelligence"] = {
        "seconds": round(market_seconds, 2),
        "status": market["status"],
        "joao": market["joao"],
        "joao_memory": market["joao_memory"],
        "b3_agents": market["b3_agents"],
        "sources": market["sources"],
        "b3_local_intelligence": market["b3_local_intelligence"],
        "macro_indicators": sorted(macro),
        "broad_market_events": len(
            market["market"].get("market_overview_research") or []
        ),
        "limitations": market["limitations"],
    }

    print(f"[2/3] Market Intelligence OK em {market_seconds:.1f}s", flush=True)
    print("[3/3] Opportunities: validando OpportunitySet + agentes...", flush=True)
    opportunities_response, opportunities_seconds = post_orchestrate(
        {
            "task": (
                "UC-03: analise WEGE3 sob demanda com dados canônicos disponíveis, "
                "mercado atual, evidências, agentes B3/DeepSeek e João Resolve. "
                "Não crie ranking ou valuation ausente."
            ),
            "ticker": "WEGE3",
            "context": {
                "workspace": "Opportunities",
                "selected_ticker": "WEGE3",
            },
        }
    )
    opportunities = require_intelligence(
        "Opportunities",
        opportunities_response,
        expected_tickers=("WEGE3",),
    )
    opportunity_result = opportunities["result"]
    canonical_set = opportunity_result.get("opportunity_set") or {}
    canonical_present = bool(canonical_set)
    if not canonical_present:
        raise SystemExit(
            "FAIL Opportunities: canonical UC-03 OpportunitySet missing"
        )
    ranked = canonical_set.get("ranked_opportunities") or []
    print(
        f"[3/3] Opportunities OK em {opportunities_seconds:.1f}s "
        f"({len(ranked)} candidato(s) executável(is))",
        flush=True,
    )
    report["opportunities"] = {
        "seconds": round(opportunities_seconds, 2),
        "status": opportunities["status"],
        "joao": opportunities["joao"],
        "joao_memory": opportunities["joao_memory"],
        "b3_agents": opportunities["b3_agents"],
        "sources": opportunities["sources"],
        "asset_evidence": opportunities["asset_evidence"],
        "b3_local_intelligence": opportunities["b3_local_intelligence"],
        "canonical_opportunity_set_present": canonical_present,
        "ranked_opportunity_count": len(ranked),
        "ranking_policy_version": canonical_set.get("ranking_policy_version"),
        "top_opportunity": ranked[0] if ranked else None,
        "limitations": opportunities["limitations"],
    }

    report["total_seconds"] = round(
        strategy_seconds + market_seconds + opportunities_seconds,
        2,
    )
    print("PASS WORKSPACE INTELLIGENCE REAL")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
