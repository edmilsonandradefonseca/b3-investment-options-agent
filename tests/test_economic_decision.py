from datetime import datetime,timezone
from copy import deepcopy
import pytest
from b3_agent.economic_decision import economic_decision
NOW=datetime(2026,10,3,tzinfo=timezone.utc)

def purchase():
    return {"rows":[{"alternative_id":ticker,"ticker":ticker,"current_price_brl":price,"capital_required_brl":1000.,"dividends":{"observed_paid_365d_gross_per_share_brl":1.,"coverage_status":"UNKNOWN_PROVIDER_COMPLETENESS"},"portfolio":{},"source_refs":["fixture"],"evidence_refs":[ticker]} for ticker,price in (("ITUB4",30.),("BBDC4",20.))]}

def inputs():
    return {"objective":"MAXIMIZE_WORST_CASE_NET_RETURN","horizon":"2027-01-01","entry_costs_brl":{"ITUB4":10.,"BBDC4":10.},"scenarios":[{"name":"down","terminal_prices_brl":{"ITUB4":27.,"BBDC4":17.},"gross_dividends_per_share_brl":{"ITUB4":1.,"BBDC4":.5},"exit_costs_brl":{"ITUB4":5.,"BBDC4":5.}},{"name":"up","terminal_prices_brl":{"ITUB4":36.,"BBDC4":23.},"gross_dividends_per_share_brl":{"ITUB4":1.,"BBDC4":.5},"exit_costs_brl":{"ITUB4":5.,"BBDC4":5.}}]}

def test_integer_sizing_cash_conservation_and_independent_net_payoff():
    result=economic_decision(purchase(),inputs(),NOW);a,b=result["rows"]
    assert a["quantity"]==33 and b["quantity"]==49
    assert a["residual_cash_brl"]==0 and b["residual_cash_brl"]==10
    assert a["scenarios"][0]["net_scenario_pnl_brl"]==-81
    assert b["scenarios"][0]["net_scenario_pnl_brl"]==-137.5
    assert a["scenarios"][0]["opportunity_cost_brl"]==-56.5
    for row in (a,b):
        assert row["purchase_notional_brl"]+row["entry_costs_brl"]+row["residual_cash_brl"]==row["budget_brl"]
    assert result["ranking"]=="CONDITIONAL_USER_SCENARIOS_ONLY" and a["rank"]==1
    assert a["expected_return"] is None and result["probabilities"] is None

def test_absent_cost_or_dividends_cannot_become_net_winner():
    for field in ("entry","dividends","exit"):
        value=inputs()
        if field=="entry": value["entry_costs_brl"].pop("ITUB4")
        else: value["scenarios"][0]["gross_dividends_per_share_brl" if field=="dividends" else "exit_costs_brl"].pop("ITUB4")
        result=economic_decision(purchase(),value,NOW)
        assert result["ranking"]=="UNKNOWN_INCOMPLETE_INPUTS"
        assert all(row["rank"] is None for row in result["rows"])

def test_zero_share_purchase_cannot_win_by_remaining_cash():
    p=purchase();p["rows"][0]["current_price_brl"]=2000
    result=economic_decision(p,inputs(),NOW)
    assert result["rows"][0]["quantity"]==0
    assert result["ranking"]=="UNKNOWN_INCOMPLETE_INPUTS"

def test_invalid_or_wrong_asset_and_duplicate_scenarios_are_rejected():
    for alter in (lambda v:v.update(horizon="2026-09-01"),lambda v:v["scenarios"].append(deepcopy(v["scenarios"][0])),lambda v:v["scenarios"][0]["terminal_prices_brl"].update(VALE3=10),lambda v:v["entry_costs_brl"].update(ITUB4=float("nan")),lambda v:v.update(probabilities=[1])):
        value=inputs();alter(value)
        with pytest.raises(ValueError): economic_decision(purchase(),value,NOW)

def test_compare_only_exposes_tradeoff_without_ranking():
    value=inputs();value["objective"]="COMPARE_ONLY"
    result=economic_decision(purchase(),value,NOW)
    assert result["ranking"]=="NOT_REQUESTED"
    assert result["rows"][0]["scenarios"][0]["opportunity_cost_brl"] is not None

def test_existing_purchase_without_new_assumptions_keeps_unknown():
    result=economic_decision(purchase(),None,NOW)
    assert result["rows"][0]["quantity"] is None
    assert result["rows"][0]["observed_distribution_yield_365d_fraction"]==pytest.approx(1/30)
