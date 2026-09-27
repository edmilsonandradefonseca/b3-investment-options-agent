from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from b3_agent.dashboard_e2e import DashboardSnapshot

@dataclass(frozen=True)
class CopilotContext:
    as_of: str
    facts: dict[str, Any]
    source_refs: tuple[str, ...]
    capabilities: tuple[str, ...] = ("EXPLAIN","COMPARE","SUMMARIZE")
    prohibited_actions: tuple[str, ...] = ("EXECUTE","PLACE_ORDER","TRADE")

class CopilotContextBuilder:
    """UC-12 deterministic boundary supplied to conversational reasoning."""
    def build(self, snapshot: DashboardSnapshot) -> CopilotContext:
        intelligence=snapshot.portfolio_intelligence
        facts={
            "portfolio": {"position_count":len(snapshot.portfolio.positions),"quality_status":snapshot.portfolio.quality_status},
            "risk": {"assignment_capital":intelligence.capital_risk.assignment_capital,"cash_known":snapshot.portfolio.cash_is_known,"cash_after_assignment":intelligence.capital_risk.cash_after_assignment,"fully_cash_secured":intelligence.capital_risk.fully_cash_secured,"uncovered_call_shares":intelligence.capital_risk.uncovered_call_shares},
            "opportunities": [{"id":x.opportunity_id,"ticker":x.ticker,"action":x.action,"attractiveness":x.attractiveness,"evidence_refs":list(x.evidence_refs)} for x in snapshot.opportunities.ranked_opportunities],
            "market_regime": None if snapshot.market_regime is None else [{"dimension":x.name.value,"label":x.label,"score":x.score} for x in snapshot.market_regime.dimensions],
            "factor_intelligence": None if snapshot.factor_study is None else [{"factor_id":x.factor_id,"adjusted_p_value":x.adjusted_p_value,"direction_stable":x.direction_stable,"significant":x.statistically_significant,"interpretation":x.interpretation} for x in snapshot.factor_study.results],
        }
        refs=tuple(dict.fromkeys((*snapshot.portfolio.source_refs,*snapshot.opportunities.source_refs)))
        return CopilotContext(snapshot.portfolio.as_of.isoformat(),facts,refs)
