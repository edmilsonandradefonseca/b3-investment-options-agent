"""Explicit, cost-aware stock purchase scenarios; never a return forecast."""
from datetime import date
from decimal import Decimal, ROUND_FLOOR
from b3_agent.stock_purchase import _number


def economic_decision(purchase, inputs, cutoff):
    inputs = inputs or {}
    if not isinstance(inputs, dict) or set(inputs)-{"objective", "horizon", "entry_costs_brl", "scenarios"}:
        raise ValueError("Unsupported economic inputs")
    objective=inputs.get("objective", "COMPARE_ONLY")
    if objective not in {"COMPARE_ONLY", "MAXIMIZE_WORST_CASE_NET_RETURN"}:
        raise ValueError("Unsupported economic objective")
    scenarios=inputs.get("scenarios", [])
    if not isinstance(scenarios,list) or len(scenarios)>9:
        raise ValueError("At most nine explicit economic scenarios are supported")
    rows=purchase["rows"]
    tickers={row["ticker"] for row in rows}
    if len(tickers)!=2 and inputs:
        raise ValueError("Economic stock scenarios require two distinct equities")
    horizon=None
    if scenarios:
        try: horizon=date.fromisoformat(str(inputs.get("horizon")))
        except ValueError: raise ValueError("An explicit economic scenario horizon is required") from None
        if horizon<=cutoff.date(): raise ValueError("Economic horizon must be future")
    names=[]
    for scenario in scenarios:
        if not isinstance(scenario,dict) or set(scenario)-{"name","terminal_prices_brl","gross_dividends_per_share_brl","exit_costs_brl"}:
            raise ValueError("Unsupported economic scenario fields")
        name=scenario.get("name")
        if not isinstance(name,str) or not name.strip() or len(name)>80 or name in names:
            raise ValueError("Economic scenarios require unique nonempty names")
        names.append(name)
        for field in ("terminal_prices_brl","gross_dividends_per_share_brl","exit_costs_brl"):
            values=scenario.get(field,{})
            if not isinstance(values,dict) or set(values)-tickers: raise ValueError("Scenario asset mismatch")
            if any(_number(value) is None or value<0 for value in values.values()): raise ValueError("Scenario amounts must be finite and nonnegative")
        if set(scenario.get("terminal_prices_brl",{}))!=tickers:
            raise ValueError("Both terminal prices are required in each economic scenario")
    entry=inputs.get("entry_costs_brl",{})
    if not isinstance(entry,dict) or set(entry)-tickers or any(_number(value) is None or value<0 for value in entry.values()):
        raise ValueError("Entry costs require exact assets and finite nonnegative amounts")
    projected=[]
    for row in rows:
        ticker=row["ticker"];spot=_number(row["current_price_brl"]);budget=_number(row["capital_required_brl"]);cost=entry.get(ticker)
        quantity=notional=residual=None
        if spot is not None and spot>0 and budget is not None and budget>0 and cost is not None and cost<=budget:
            price=Decimal(str(spot));capital=Decimal(str(budget));fee=Decimal(str(cost))
            quantity=int(((capital-fee)/price).to_integral_value(rounding=ROUND_FLOOR))
            notional=float(price*quantity);residual=float(capital-fee-price*quantity)
        payouts=[]
        for scenario in scenarios:
            terminal=scenario["terminal_prices_brl"][ticker]
            dividend=scenario.get("gross_dividends_per_share_brl",{}).get(ticker)
            exit_cost=scenario.get("exit_costs_brl",{}).get(ticker)
            final=pnl=ratio=breakeven=None
            if quantity is not None and dividend is not None and exit_cost is not None:
                final=float(Decimal(str(residual))+quantity*(Decimal(str(terminal))+Decimal(str(dividend)))-Decimal(str(exit_cost)))
                pnl=float(Decimal(str(final))-Decimal(str(budget)))
                ratio=pnl/budget
                if quantity>0: breakeven=(budget-residual+exit_cost-quantity*dividend)/quantity
            payouts.append({"name":scenario["name"],"terminal_price_brl":terminal,"user_gross_dividend_per_share_brl":dividend,
                "user_exit_costs_brl":exit_cost,"final_value_brl":final,"net_scenario_pnl_brl":pnl,
                "net_scenario_return_fraction":ratio,"breakeven_terminal_price_brl":breakeven,"opportunity_cost_brl":None})
        observed=row["dividends"].get("observed_paid_365d_gross_per_share_brl")
        projected.append({"alternative_id":row["alternative_id"],"ticker":ticker,"budget_brl":budget,
            "entry_costs_brl":cost,"quantity":quantity,"purchase_notional_brl":notional,"residual_cash_brl":residual,
            "observed_distribution_yield_365d_fraction":observed/spot if observed is not None and spot else None,
            "coverage_status":row["dividends"].get("coverage_status"),
            "stock_quantity_before":row["portfolio"].get("stock_quantity") if row["portfolio"].get("snapshot_as_of") else None,
            "scenarios":payouts,"rank":None,"expected_return":None,"positive_return_probability":None,
            "source_refs":row["source_refs"],"evidence_refs":row["evidence_refs"]})
    complete=bool(scenarios) and all(row["quantity"] is not None and row["quantity"]>0 and all(s["net_scenario_pnl_brl"] is not None for s in row["scenarios"]) for row in projected)
    ranking="NOT_REQUESTED" if objective=="COMPARE_ONLY" else "UNKNOWN_INCOMPLETE_INPUTS"
    if complete:
        for i,row in enumerate(projected):
            for j,scenario in enumerate(row["scenarios"]):
                scenario["opportunity_cost_brl"]=projected[1-i]["scenarios"][j]["net_scenario_pnl_brl"]-scenario["net_scenario_pnl_brl"]
        if objective!="COMPARE_ONLY":
            worst=[min(s["net_scenario_return_fraction"] for s in row["scenarios"]) for row in projected]
            if abs(worst[0]-worst[1])<1e-12:
                ranking="TIE";projected[0]["rank"]=projected[1]["rank"]=1
            else:
                winner=0 if worst[0]>worst[1] else 1
                projected[winner]["rank"]=1;projected[1-winner]["rank"]=2;ranking="CONDITIONAL_USER_SCENARIOS_ONLY"
    return {"policy_version":"economic-stock-scenarios-v1","objective":objective,"ranking":ranking,
        "horizon":horizon,"rows":projected,"scenario_coverage":"COMPLETE" if complete else "PARTIAL_OR_NOT_REQUESTED",
        "assumption_origin":"USER_SUPPLIED_WHAT_IF_NOT_FORECAST","probabilities":None,
        "limitations":["Terminal prices, dividend amounts and costs are user what-if assumptions, not broker forecasts or predicted return.",
            "Entry and exit costs must explicitly cover modeled fees, taxes and slippage; omitted amounts remain UNKNOWN, including dividends.",
            "Integer shares use a one-share model, not executable orders; residual cash earns zero in this stated scenario.",
            "Observed 365-day issuer distribution yield has unproven coverage and is not forward yield or personal income.",
            "Conditional maximin ranks only the complete supplied scenario set; it is not an overall investment recommendation."]}
