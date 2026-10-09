#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from b3_agent.jobs.continuous_intelligence import _monitored_tickers
from b3_agent.server import OrchestrateRequest, orchestrate


def _safe_summary(response: Any) -> dict[str, Any]:
    result = response.result if isinstance(response.result, dict) else {}
    screen = result.get("opportunity_screen")
    screen = screen if isinstance(screen, dict) else {}
    scope = result.get("opportunity_research_scope")
    scope = scope if isinstance(scope, dict) else {}
    proposal = result.get("decision_proposal")
    proposal = proposal if isinstance(proposal, dict) else {}
    assessments = proposal.get("alternative_assessments")
    assessments = assessments if isinstance(assessments, list) else []
    return {
        "status": response.status,
        "derived_synthesis_status": result.get("derived_synthesis_status"),
        "screened_stock_count": scope.get("screened_stock_count"),
        "contextual_research_count": scope.get("contextual_research_count"),
        "deterministic_only_count": scope.get("deterministic_only_count"),
        "qualified_opportunity_count": sum(
            1 for item in assessments
            if isinstance(item, dict)
            and item.get("opportunity_status") == "QUALIFIED_OPPORTUNITY"
            and int(item.get("priority_rank") or 0) > 0
        ),
        "run_id": result.get("opportunity_review_run_id"),
    }


def main() -> int:
    tickers = list(_monitored_tickers())
    if not tickers:
        print(json.dumps({"status": "NO_MONITORED_TICKERS"}))
        return 2

    task = (
        "Revisão diária completa UC-03: analise todas as ações monitoradas e todas "
        "as ações do snapshot vigente. Cruze notícias/eventos datados, histórico "
        "recente de preço e volume, fundamentos disponíveis, curvas futuras B3 "
        "PRE/DIC e exposição da carteira. Classifique cada ativo como oportunidade "
        "qualificada, acompanhar, evidência insuficiente ou tese rejeitada. Ordene "
        "somente as oportunidades qualificadas por prioridade de revisão, citando "
        "evidências e contrapontos. Se nenhuma se qualificar, retorne ranking vazio "
        "e explique as lacunas. Nunca infira retorno esperado nem emita ordem."
    )
    response = orchestrate(
        OrchestrateRequest(
            task=task,
            ticker=None,
            context={
                "workspace": "Opportunities",
                "dashboard_page": "Opportunities",
                "selected_ticker": None,
                "opportunity_assets": tickers,
                "opportunity_objective": "COMPARE_ONLY",
                "include_portfolio_stocks": True,
                "include_yield_curve": True,
                "research_mode": "refresh",
            },
        )
    )
    summary = _safe_summary(response)
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if summary.get("derived_synthesis_status") == "COMPLETED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
