from datetime import date
from b3_agent.copilot_context import CopilotContextBuilder
from b3_agent.dashboard_e2e import DashboardSnapshot
from b3_agent.portfolio.capital_risk import CapitalRiskSnapshot
from b3_agent.portfolio.context import PortfolioIntelligence
from b3_agent.schemas.opportunity import OpportunitySet
from b3_agent.schemas.position import PortfolioContext

def test_uc12_copilot_context_is_fact_boundary_and_cannot_trade():
    portfolio=PortfolioContext(date(2026,9,27),(),cash_is_known=False,source_refs=("BTG:Renda Variavel",))
    risk=CapitalRiskSnapshot(0,1000,None,None,0)
    intelligence=PortfolioIntelligence(portfolio.as_of,(),(),risk)
    opportunities=OpportunitySet(as_of=portfolio.as_of,ranked_opportunities=(),source_refs=("market",))
    snapshot=DashboardSnapshot(portfolio,intelligence,(),opportunities)
    context=CopilotContextBuilder().build(snapshot)
    assert context.facts["risk"]["cash_known"] is False
    assert context.facts["risk"]["fully_cash_secured"] is None
    assert context.source_refs == ("BTG:Renda Variavel","market")
    assert "EXPLAIN" in context.capabilities
    assert set(("EXECUTE","PLACE_ORDER","TRADE")) <= set(context.prohibited_actions)
