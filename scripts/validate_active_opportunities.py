"""Focused integrated Opportunities acceptance against the active Ubuntu HTTP service.

Full portfolio and response details stay in a mode-0600 local report. Console
output is metadata only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path("scripts").resolve()))
from validate_live_workspace_outputs import call_json, write_private_report

BASE_URL = "http://127.0.0.1:8000"
CANDIDATES = ["ITUB4", "BBDC4"]


def main() -> int:
    health = call_json(f"{BASE_URL}/health", None, 15)
    assert health["http_status"] == 200 and not health["transport_error_type"], "Active B3 service is unhealthy"

    snapshot_result = call_json(f"{BASE_URL}/portfolio/current", None, 15)
    assert snapshot_result["http_status"] == 200 and not snapshot_result["transport_error_type"], "Active portfolio snapshot unavailable"
    portfolio = snapshot_result["response"] or {}
    positions = portfolio.get("positions") or []
    assert positions, "Active portfolio snapshot is empty"

    stock_tickers = {
        str(position.get("ticker", "")).strip().upper()
        for position in positions
        if str(position.get("instrument_type", "")).upper() == "STOCK" and position.get("ticker")
    }
    option_underlyings = {
        str(position.get("underlying_ticker", "")).strip().upper()
        for position in positions
        if str(position.get("instrument_type", "")).upper() == "OPTION" and position.get("underlying_ticker")
    }
    request = {
        "task": (
            "UC-03: revise as ações acompanhadas e toda a carteira vigente. "
            "Use triagem determinística, contexto de ações e opções já possuídas "
            "e evidências disponíveis. Apresente síntese sênior com cobertura, "
            "materialidade, evidências e limitações. Não invente retorno, "
            "probabilidade nem recomendação automática."
        ),
        "ticker": None,
        "context": {
            "workspace": "Opportunities",
            "selected_ticker": None,
            "opportunity_assets": CANDIDATES,
            "opportunity_objective": "LOWEST_REALIZED_VOLATILITY_60D",
            "include_portfolio_stocks": True,
            "research_mode": "stored_only",
        },
    }
    response = call_json(f"{BASE_URL}/orchestrate", request, 240)
    write_private_report(
        Path.home() / ".local/share/b3-investment-options-agent/live-validation/active-opportunities-integrated",
        {"instance": "ACTIVE HTTP systemd", "request": request, "response": response},
    )
    body = response.get("response") or {}
    assert response["http_status"] == 200 and not body.get("error"), "Integrated Opportunities HTTP request failed"
    result = body.get("result") or {}
    screen = result.get("opportunity_screen") or {}
    scope = result.get("opportunity_research_scope") or {}
    assert result.get("derived_synthesis_status") == "COMPLETED", "Senior synthesis did not complete"
    assert screen.get("candidate_universe") == CANDIDATES, "Candidate universe changed"
    actual_stocks = set(screen.get("portfolio_stock_universe") or [])
    actual_options = set(screen.get("portfolio_option_underlying_universe") or [])
    actual_union = set(screen.get("requested_universe") or [])
    expected_union = set(CANDIDATES) | stock_tickers | option_underlyings
    assert actual_stocks == stock_tickers, "Active screen omitted or added stock snapshot positions"
    assert actual_options == option_underlyings, "Active screen omitted or added option exposure underlyings"
    assert actual_union == expected_union, "Active screen silently truncated the full portfolio/candidate union"
    assert len(screen.get("rows") or []) == len(expected_union), "Active screen row coverage is incomplete"
    assert scope.get("policy_version") == "B3_OPPORTUNITY_RESEARCH_ENRICHMENT_V1"
    context_tickers = scope.get("context_tickers") or []
    assert len(context_tickers) <= 8, "Contextual research budget exceeded"
    assert scope.get("screened_stock_count") == scope.get("contextual_research_count", 0) + scope.get("deterministic_only_count", 0)
    synthesis = result.get("synthesis") or {}
    proposal = result.get("decision_proposal") or result.get("proposal") or {}
    narrative = next(
        (
            value
            for value in (
                synthesis.get("summary"),
                proposal.get("thesis"),
                proposal.get("rationale"),
                result.get("summary"),
            )
            if isinstance(value, str) and value.strip()
        ),
        None,
    )
    assert narrative, "Senior Opportunities narrative is empty"
    material = screen.get("material_candidates") or []
    assert all(item.get("why_now") and item.get("evidence_refs") for item in material), "Material thesis lacks evidence provenance"

    print(
        json.dumps(
            {
                "case": "ACTIVE_INTEGRATED_OPPORTUNITIES",
                "http": response["http_status"],
                "elapsed_ms": response["elapsed_ms"],
                "synthesis_status": result.get("derived_synthesis_status"),
                "candidate_count": len(screen.get("candidate_universe") or []),
                "portfolio_stock_count": len(actual_stocks),
                "option_underlying_count": len(actual_options),
                "requested_universe_count": len(actual_union),
                "research_context_count": scope.get("contextual_research_count"),
                "material_review_count": len(material),
                "source_count": len(body.get("sources") or []),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    print("ACTIVE_INTEGRATED_OPPORTUNITIES=PASS", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
