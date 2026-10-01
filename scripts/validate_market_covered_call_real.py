#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone
import json

from b3_agent.config import settings
from b3_agent.intelligence.workspace_context import (
    WorkspaceIntelligenceContextService,
)
from b3_agent.opportunity_live import LiveOpportunityService
from b3_agent.portfolio.snapshot import load_active_snapshots
from b3_agent.providers.oplab.options import OplabOptionsAdapter
from b3_agent.schemas.position import PortfolioContext
from b3_agent.strategy_live import LiveStrategyComparisonService


def _active_portfolio() -> PortfolioContext:
    snapshots = load_active_snapshots(settings.data_dir)
    portfolio = snapshots.get("portfolio_context")
    if not isinstance(portfolio, PortfolioContext):
        raise SystemExit(
            "FAIL no canonical portfolio snapshot; import portfolio.xlsx first"
        )
    return portfolio


def _covered_call_candidate(portfolio: PortfolioContext) -> dict:
    now = datetime.now(timezone.utc)
    provider = OplabOptionsAdapter()
    holdings = sorted(
        (
            position
            for position in portfolio.positions
            if position.instrument_type.upper() != "OPTION"
            and position.quantity > 0
        ),
        key=lambda item: abs(float(item.market_value or 0.0)),
        reverse=True,
    )

    diagnostics: list[dict] = []
    for position in holdings[:20]:
        ticker = position.ticker.upper()
        try:
            contracts, quotes = provider.get_snapshot(ticker, now)
        except (OSError, RuntimeError, ValueError) as exc:
            diagnostics.append({"ticker": ticker, "error": str(exc)})
            continue

        quotes_by_id = {item.option_id: item for item in quotes}
        eligible = []
        for contract in contracts:
            if contract.option_type.upper() != "CALL":
                continue
            if contract.expiration_date <= now.date():
                continue
            if float(contract.contract_multiplier) > float(position.quantity):
                continue
            quote = quotes_by_id.get(contract.option_id)
            if quote is None:
                continue
            if quote.bid is None or quote.bid <= 0:
                continue
            if quote.ask is None or quote.ask <= 0:
                continue
            eligible.append((contract, quote))

        if not eligible:
            diagnostics.append({
                "ticker": ticker,
                "stock_quantity": position.quantity,
                "eligible_calls": 0,
            })
            continue

        eligible.sort(
            key=lambda pair: (
                -(float(pair[1].volume or 0.0)),
                pair[0].expiration_date,
                pair[0].strike,
                pair[0].option_id,
            )
        )
        contract, quote = eligible[0]
        return {
            "ticker": ticker,
            "stock_quantity": float(position.quantity),
            "contract": contract,
            "quote": quote,
            "diagnostics": diagnostics,
        }

    raise SystemExit(
        "FAIL no held stock has an executable covered CALL in the current "
        f"OPLAB chain. diagnostics={json.dumps(diagnostics, default=str)}"
    )


def main() -> None:
    report: dict[str, object] = {}

    print("[1/3] Market Intelligence research PIT...", flush=True)
    context = WorkspaceIntelligenceContextService().build(
        workspace="Market Intelligence",
        tickers=(),
        deterministic_result={},
        include_joao=False,
        news_limit=8,
    )
    market = context.deterministic_context["market_analysis"]
    events = market.get("market_overview_research") or []
    diagnostics = market.get("market_overview_diagnostics") or []
    normalized_seen = max(
        (
            int(item.get("normalized_result_count") or 0)
            for item in diagnostics
            if isinstance(item, dict)
        ),
        default=0,
    )
    if normalized_seen > 0 and not events:
        raise SystemExit(
            "FAIL research PIT: provider normalized live results but the "
            "workspace discarded every event"
        )
    if not events:
        raise SystemExit(
            "FAIL research coverage: no broad-market event available from "
            "SearXNG or Google News RSS"
        )
    print(
        f"[1/3] Market research OK · eventos={len(events)} "
        f"· normalized_seen={normalized_seen}",
        flush=True,
    )
    report["market_research"] = {
        "events": len(events),
        "normalized_seen": normalized_seen,
        "first_event": events[0],
        "diagnostics": diagnostics,
    }

    print("[2/3] Procurando covered CALL real na carteira...", flush=True)
    portfolio = _active_portfolio()
    candidate = _covered_call_candidate(portfolio)
    ticker = candidate["ticker"]
    contract = candidate["contract"]
    quote = candidate["quote"]
    print(
        f"[2/3] Candidato: {ticker} {contract.option_id} "
        f"strike={contract.strike} bid={quote.bid} "
        f"ações={candidate['stock_quantity']}",
        flush=True,
    )

    comparison = LiveStrategyComparisonService().compare(
        assets=(ticker, ticker),
        strategies=("Manter", "Vender CALL coberta"),
        option_ids=(None, contract.option_id),
        portfolio=portfolio,
        as_of=datetime.now(timezone.utc),
    )
    evidence = (comparison.get("option_evidence") or {}).get(
        contract.option_id
    ) or {}
    call = evidence.get("call_analysis") or {}
    current = evidence.get("current_quote") or {}
    if not call:
        raise SystemExit("FAIL Strategy Lab covered CALL call_analysis missing")
    if current.get("source") != "oplab":
        raise SystemExit("FAIL Strategy Lab covered CALL quote is not OPLAB")
    if current.get("bid") is None or current.get("bid") <= 0:
        raise SystemExit("FAIL Strategy Lab covered CALL executable bid missing")
    if evidence.get("stock_shares_available", 0) < evidence.get(
        "covered_shares_required", 1
    ):
        raise SystemExit("FAIL Strategy Lab accepted an uncovered CALL")

    print("[2/3] Strategy Lab covered CALL OK", flush=True)
    report["strategy_lab_covered_call"] = {
        "ticker": ticker,
        "option_id": contract.option_id,
        "strike": contract.strike,
        "expiration_date": contract.expiration_date,
        "bid": current.get("bid"),
        "ask": current.get("ask"),
        "premium_return": call.get("premium_return"),
        "annualized_premium_return": call.get(
            "annualized_premium_return"
        ),
        "gain_to_strike": call.get("gain_to_strike"),
        "total_return_if_assigned": call.get(
            "total_return_if_assigned"
        ),
        "stock_shares_available": evidence.get(
            "stock_shares_available"
        ),
        "covered_shares_required": evidence.get(
            "covered_shares_required"
        ),
    }

    print("[3/3] UC-03 covered CALL candidate...", flush=True)
    opportunities = LiveOpportunityService().build(
        ticker,
        as_of=datetime.now(timezone.utc),
        limit=500,
        portfolio=portfolio,
    )
    ids = {
        item.opportunity_id: item
        for item in opportunities.opportunity_set.ranked_opportunities
    }
    expected = f"SELL_CALL:{contract.option_id}"
    if expected not in ids:
        call_ids = sorted(
            key for key in ids if key.startswith("SELL_CALL:")
        )
        raise SystemExit(
            f"FAIL UC-03 covered CALL {expected} missing; "
            f"available_calls={call_ids[:20]}"
        )
    opportunity = ids[expected]
    marketability = opportunities.option_marketability.get(
        contract.option_id
    ) or {}
    if marketability.get("covered_call") is not True:
        raise SystemExit("FAIL UC-03 CALL candidate lacks covered-call evidence")

    print(
        f"[3/3] Opportunities covered CALL OK · "
        f"total={len(ids)} · calls={sum(k.startswith('SELL_CALL:') for k in ids)}",
        flush=True,
    )
    report["opportunities"] = {
        "total_candidates": len(ids),
        "covered_call_candidates": sum(
            key.startswith("SELL_CALL:") for key in ids
        ),
        "validated_candidate": {
            "opportunity_id": opportunity.opportunity_id,
            "action": opportunity.action,
            "expected_return": opportunity.expected_return,
            "capital_requirement": opportunity.capital_requirement,
        },
        "marketability": marketability,
        "ranking_status": opportunities.ranking_status,
        "ranking_reason": opportunities.ranking_reason,
    }

    print("PASS MARKET + COVERED CALL REAL")
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
