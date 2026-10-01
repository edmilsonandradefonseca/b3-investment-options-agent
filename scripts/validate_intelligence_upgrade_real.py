#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request


BASE_URL = os.getenv("B3_API_URL", "http://127.0.0.1:8000").rstrip("/")
TIMEOUT = float(os.getenv("B3_INTELLIGENCE_UPGRADE_TIMEOUT_SECONDS", "180"))
STARTUP_TIMEOUT = float(os.getenv("B3_WORKSPACE_STARTUP_TIMEOUT_SECONDS", "45"))


def wait_for_runtime() -> float:
    started = time.monotonic()
    deadline = started + STARTUP_TIMEOUT
    last_error = "not attempted"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{BASE_URL}/health", timeout=2.0) as response:
                if 200 <= response.status < 300:
                    return time.monotonic() - started
                last_error = f"HTTP {response.status}"
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = str(exc)
        time.sleep(0.5)
    raise SystemExit(
        f"FAIL runtime health after {STARTUP_TIMEOUT:.0f}s: {last_error}"
    )


def orchestrate(payload: dict) -> tuple[dict, float]:
    request = urllib.request.Request(
        f"{BASE_URL}/orchestrate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
    )
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"FAIL HTTP {exc.code}: {raw}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise SystemExit(
            f"FAIL transport {type(exc).__name__}: {exc}"
        ) from exc
    if not isinstance(body, dict):
        raise SystemExit("FAIL orchestrate returned non-object")
    if body.get("error"):
        raise SystemExit(f"FAIL orchestrate: {body['error']}")
    return body, time.monotonic() - started


def result_workspace(response: dict) -> tuple[dict, dict, dict]:
    result = response.get("result") or {}
    workspace = result.get("workspace_intelligence") or {}
    if not workspace:
        raise SystemExit("FAIL workspace_intelligence missing")
    derived = workspace.get("derived_intelligence") or {}
    joao = derived.get("joao_resolve") or {}
    if joao.get("status") != "READY":
        raise SystemExit(
            f"FAIL João Resolve status={joao.get('status')} "
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
            raise SystemExit(f"FAIL B3 agent output missing: {key}")
    return result, workspace, derived


def main() -> None:
    print("[0/2] Aguardando runtime...", flush=True)
    startup = wait_for_runtime()
    print(f"[0/2] Runtime saudável em {startup:.1f}s", flush=True)

    print("[1/2] Market Intelligence...", flush=True)
    market_response, market_seconds = orchestrate({
        "task": (
            "UC-05/06/10: produza inteligência de mercado atual integrando macro, "
            "research/events e agentes B3/João. Preserve fatos, fontes, incertezas "
            "e não invente evidências."
        ),
        "ticker": None,
        "context": {
            "workspace": "Market Intelligence",
            "selected_ticker": None,
            "asset_view": False,
        },
    })
    _, market_workspace, market_derived = result_workspace(market_response)
    market_context = market_workspace.get("market_context") or {}
    macro = market_context.get("macro") or {}
    if not all(key in macro for key in ("SELIC", "CDI", "IPCA")):
        raise SystemExit("FAIL Market Intelligence macro incomplete")
    events = market_context.get("market_overview_research") or []
    diagnostics = market_context.get("market_overview_diagnostics") or []
    research_state = "READY" if events else "LIMITED"
    print(
        f"[1/2] Market Intelligence OK em {market_seconds:.1f}s "
        f"· eventos={len(events)} · research={research_state}",
        flush=True,
    )

    print("[2/2] Opportunities...", flush=True)
    opp_response, opp_seconds = orchestrate({
        "task": (
            "UC-03: analise WEGE3 usando somente oportunidades canônicas, "
            "dados atuais, mercado, carteira e agentes B3/João. Retorno anualizado "
            "é evidência e não deve, sozinho, definir ranking econômico."
        ),
        "ticker": "WEGE3",
        "context": {
            "workspace": "Opportunities",
            "selected_ticker": "WEGE3",
        },
    })
    opp_result, opp_workspace, opp_derived = result_workspace(opp_response)
    opportunity_set = opp_result.get("opportunity_set") or {}
    if not opportunity_set:
        raise SystemExit("FAIL canonical OpportunitySet missing")
    ranking_status = opp_result.get("opportunity_ranking_status")
    ranking_reason = opp_result.get("opportunity_ranking_reason")
    if ranking_status != "DEFERRED_INCOMPLETE_CONTEXT":
        raise SystemExit(
            "FAIL expected deferred economic ranking with incomplete context, "
            f"got {ranking_status!r}"
        )
    if not ranking_reason:
        raise SystemExit("FAIL ranking reason missing")
    candidates = opportunity_set.get("ranked_opportunities") or []
    marketability = opp_result.get("option_marketability") or {}
    if candidates and not marketability:
        raise SystemExit("FAIL option marketability missing for candidates")

    first = candidates[0] if candidates else None
    first_marketability = {}
    if isinstance(first, dict):
        option_id = first.get("options_analysis_ref")
        if option_id:
            first_marketability = marketability.get(option_id) or {}

    print(
        f"[2/2] Opportunities OK em {opp_seconds:.1f}s "
        f"· candidatos={len(candidates)} · ranking={ranking_status}",
        flush=True,
    )

    report = {
        "market_intelligence": {
            "seconds": round(market_seconds, 2),
            "status": market_response.get("status"),
            "macro_indicators": sorted(macro),
            "broad_market_events": len(events),
            "research_status": research_state,
            "research_diagnostics": diagnostics,
            "joao_status": (market_derived.get("joao_resolve") or {}).get("status"),
            "limitations": market_workspace.get("limitations") or [],
        },
        "opportunities": {
            "seconds": round(opp_seconds, 2),
            "status": opp_response.get("status"),
            "candidate_count": len(candidates),
            "ranking_policy_version": opportunity_set.get("ranking_policy_version"),
            "ranking_status": ranking_status,
            "ranking_reason": ranking_reason,
            "first_candidate": first,
            "first_candidate_marketability": first_marketability,
            "joao_status": (opp_derived.get("joao_resolve") or {}).get("status"),
            "limitations": opp_workspace.get("limitations") or [],
        },
        "total_seconds": round(market_seconds + opp_seconds, 2),
    }
    print("PASS INTELLIGENCE UPGRADE REAL")
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
