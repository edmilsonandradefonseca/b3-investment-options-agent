"""Focused acceptance against the active systemd HTTP process; no worker replay."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path("scripts").resolve()))
from validate_live_workspace_outputs import call_json, write_private_report
base = "http://127.0.0.1:8000"
health = call_json(base + "/health", None, 15)
assert health["http_status"] == 200 and not health["transport_error_type"]
request = {"task":"Compare ITUB4 and BBDC4 purchases using qualified evidence; keep forward forecasts UNKNOWN.", "context":{"workspace":"Strategy Lab","comparison_assets":["ITUB4","BBDC4"],"strategy_a":"Comprar ação","strategy_b":"Comprar ação","comparison_amount":10000,"analysis_mode":"deterministic","research_mode":"stored_only"}}
response = call_json(base + "/orchestrate", request, 90)
write_private_report(Path.home()/".local/share/b3-investment-options-agent/live-validation/active-stock-purchase", {"instance":"ACTIVE HTTP systemd","response":response})
body = response.get("response") or {}
assert response["http_status"] == 200 and not body.get("error")
result = body["result"]
pair = result["stock_purchase_comparison"]
assert pair["policy_version"] == "stock-buy-evidence-v1"
assert result["telemetry"]["llm_calls"] == 0
rows = pair["rows"]
assert len(rows) == 2 and {row["ticker"] for row in rows} == {"ITUB4","BBDC4"}
assert all(row["current_price_brl"] is not None and row["capital_required_brl"] == 10000 for row in rows)
brapi_budget = call_json(base + "/providers/budget/brapi", None, 15)
print(json.dumps({"case":"ACTIVE_BRAPI_BUDGET","http":brapi_budget["http_status"],"budget":brapi_budget.get("response")},ensure_ascii=False),flush=True)
print(json.dumps({"case":"ACTIVE_FUNDAMENTAL_DIAGNOSTIC","rows":[{"ticker":row["ticker"],"admitted_count":len(row.get("fundamental_metrics") or {}),"excluded_metrics":row.get("excluded_metrics") or [],"source_refs":row.get("source_refs") or [],"provider":((result.get("asset_evidence") or {}).get(row["ticker"]) or {}).get("fundamentals",{}).get("provider"),"metric_count":((result.get("asset_evidence") or {}).get(row["ticker"]) or {}).get("fundamentals",{}).get("metric_count"),"fundamental_limitations":[item for item in ((result.get("asset_evidence") or {}).get(row["ticker"]) or {}).get("limitations",[]) if "Fundamentals" in item]} for row in rows]},ensure_ascii=False),flush=True)
missing_fundamentals = [row["ticker"] for row in rows if not row.get("fundamental_metrics")]
asset_evidence = result.get("asset_evidence") or {}
for ticker in missing_fundamentals:
    limitations = ((asset_evidence.get(ticker) or {}).get("limitations") or [])
    assert any(str(item).startswith(f"Fundamentals unavailable for {ticker}:") for item in limitations), f"{ticker} has no fundamentals and no explicit provider limitation"
print(json.dumps({"case":"ACTIVE_FUNDAMENTALS","status":"PARTIAL_PROVIDER_UNAVAILABLE" if missing_fundamentals else "PASS","tickers":missing_fundamentals},ensure_ascii=False),flush=True)
assert all(row["expected_return"] is None and row["future_dividend_per_share"] is None for row in rows)
assert {row["alternative_id"] for row in rows} == {row["alternative_id"] for row in result["strategy_comparison"]["alternatives"]}
assert all(row["dividends"]["policy_version"] == "issuer-dividends-v1" for row in rows)
assert all(row["dividends"]["read_origin"] == "STORED_ASYNC_SNAPSHOT" for row in rows), "Active process still uses inline dividend collection"
assert any(row["dividends"]["events"] for row in rows)
bradesco = next(row["dividends"] for row in rows if row["ticker"] == "BBDC4")
assert bradesco["collection_status"] == "READ_OK"
assert bradesco["coverage_status"] == "PARTIAL_MONTHLY_JCP_ONLY"
assert len(bradesco["events"]) == 12
from b3_agent.providers.bradesco_dividends import DOCUMENT_PREFIX
for event in bradesco["events"]:
    assert event["source"].startswith(DOCUMENT_PREFIX)
    assert event["gross_amount_per_share_brl"] == 0.018974809
    assert "PARTIAL_MONTHLY_JCP_ONLY" in event["quality_flags"]
    if event["announcement_date"] is None:
        assert event["payment_status"] == "FUTURE_PAYMENT_UNVERIFIED_ANNOUNCEMENT"
        assert "SCHEDULED_NOT_YET_DECLARED" in event["quality_flags"]

assert all(row["institution_targets"]["policy_version"] == "stored-institution-targets-v1" for row in rows)
assert all(row["institution_targets"]["rows"] for row in rows), "Expected ingested primary reports on active runtime"
print(json.dumps({"case":"ACTIVE_INSTITUTION_TARGETS","statuses":[row["institution_targets"]["status"] for row in rows],"counts":[len(row["institution_targets"]["rows"]) for row in rows]}),flush=True)
print(json.dumps({"case":"ACTIVE_DIVIDENDS","collection":[row["dividends"]["collection_status"] for row in rows],"event_counts":[len(row["dividends"]["events"]) for row in rows]}),flush=True)
print(json.dumps({"case":"ACTIVE_STOCK_PURCHASE","http":200,"elapsed_ms":response["elapsed_ms"],"fundamental_counts":[len(row["fundamental_metrics"]) for row in rows],"llm_calls":0}),flush=True)
print("ACTIVE_STOCK_PURCHASE=PASS RUNTIME_MUTATIONS=NONE",flush=True)
from datetime import datetime, timedelta, timezone
prices = {row["ticker"]: row["current_price_brl"] for row in rows}
request["context"]["economic_inputs"] = {"objective":"MAXIMIZE_WORST_CASE_NET_RETURN","horizon":(datetime.now(timezone.utc).date()+timedelta(days=90)).isoformat(),"entry_costs_brl":{"ITUB4":0,"BBDC4":0},"scenarios":[{"name":"Explicit hypothetical comparison","terminal_prices_brl":{"ITUB4":prices["ITUB4"]*.95,"BBDC4":prices["BBDC4"]*.90},"gross_dividends_per_share_brl":{"ITUB4":0,"BBDC4":0},"exit_costs_brl":{"ITUB4":0,"BBDC4":0}}]}
economic_response = call_json(base + "/orchestrate", request, 90)
write_private_report(Path.home()/".local/share/b3-investment-options-agent/live-validation/active-economic-decision", {"instance":"ACTIVE HTTP systemd","response":economic_response})
body=economic_response.get("response") or {}
assert economic_response["http_status"]==200 and not body.get("error")
result=body["result"];economic=result["economic_decision"]
assert economic["policy_version"]=="economic-stock-scenarios-v1"
assert result["telemetry"]["llm_calls"]==0
assert economic["ranking"]=="CONDITIONAL_USER_SCENARIOS_ONLY"
assert {row["alternative_id"] for row in economic["rows"]}=={row["alternative_id"] for row in result["strategy_comparison"]["alternatives"]}
for row in economic["rows"]:
    assert row["quantity"]>0 and row["scenarios"][0]["net_scenario_pnl_brl"] is not None
    assert abs(row["purchase_notional_brl"]+row["entry_costs_brl"]+row["residual_cash_brl"]-row["budget_brl"])<1e-7
    assert row["expected_return"] is None and row["positive_return_probability"] is None
print(json.dumps({"case":"ACTIVE_ECONOMIC_DECISION","http":200,"elapsed_ms":economic_response["elapsed_ms"],"cash_conservation":"PASS","llm_calls":0}),flush=True)

for row in result["stock_purchase_comparison"]["rows"]:
    evidence=row["economic_evidence"]
    assert evidence["quantity"]>0 and evidence["institution_target_potential"]
    assert evidence["expected_return"] is None
    assert abs(evidence["notional_brl"]+evidence["entry_cost_brl"]+evidence["residual_cash_brl"]-10000)<1e-7
opportunity_request={"task":"Compare verified institution target potential, keeping forecast fields unknown.","context":{"workspace":"Opportunities","opportunity_assets":["ITUB4","BBDC4"],"analysis_mode":"deterministic","opportunity_economic_inputs":{"budget_brl":10000,"entry_costs_brl":{"ITUB4":0,"BBDC4":0},"target_institution":"XP","target_horizon":"2027-12-31"}}}
opportunity_response=call_json(base+"/orchestrate",opportunity_request,90)
write_private_report(Path.home()/".local/share/b3-investment-options-agent/live-validation/active-sourced-opportunities",{"instance":"ACTIVE HTTP systemd","response":opportunity_response})
body=opportunity_response.get("response") or {}
assert opportunity_response["http_status"]==200 and not body.get("error")
result=body["result"]
assert result["telemetry"]["llm_calls"]==0
ranking=result["economic_target_ranking"]
assert ranking["status"]=="CONDITIONAL_TARGET_POTENTIAL" and len(ranking["rows"])==2
for row in result["opportunity_screen"]["rows"]:
    assert row["dividends"]["read_origin"] == "STORED_ASYNC_SNAPSHOT"
    evidence=row["economic_evidence"]
    assert evidence["quantity"]>0 and evidence["institution_target_potential"]
    assert abs(evidence["notional_brl"]+evidence["entry_cost_brl"]+evidence["residual_cash_brl"]-10000)<1e-7
    assert evidence["expected_return"] is None
print(json.dumps({"case":"ACTIVE_SOURCED_OPPORTUNITIES","http":200,"elapsed_ms":opportunity_response["elapsed_ms"],"target_count":sum(len(row["economic_evidence"]["institution_target_potential"]) for row in result["opportunity_screen"]["rows"]),"cash_conservation":"PASS","llm_calls":0}),flush=True)

# Exercise the same integrated contract used by the Opportunities workspace UI
# against the active systemd process after the candidate revision is installed.
snapshot_response=call_json(base+"/portfolio/current",None,15)
assert snapshot_response["http_status"]==200 and not snapshot_response["transport_error_type"]
snapshot=snapshot_response["response"] or {}
positions=snapshot.get("positions") or []
expected_stock={str(p.get("ticker","")).upper() for p in positions
    if str(p.get("instrument_type","")).upper()=="STOCK" and p.get("ticker")}
expected_option_underlyings={str(p.get("underlying_ticker","")).upper() for p in positions
    if str(p.get("instrument_type","")).upper()=="OPTION" and p.get("underlying_ticker")}
integrated_request={"task":"UC-03: revise as ações acompanhadas e toda a carteira vigente. Use triagem determinística, contexto de ações e opções já possuídas, evidências disponíveis e síntese sênior. Explique cobertura e limitações sem inventar recomendação, retorno ou probabilidade.",
    "context":{"workspace":"Opportunities","selected_ticker":None,"opportunity_assets":["ITUB4","BBDC4"],
        "opportunity_objective":"LOWEST_REALIZED_VOLATILITY_60D","include_portfolio_stocks":True,"research_mode":"stored_only"}}
integrated_response=call_json(base+"/orchestrate",integrated_request,240)
write_private_report(Path.home()/".local/share/b3-investment-options-agent/live-validation/active-opportunities-integrated",
    {"instance":"ACTIVE HTTP systemd after tested revision install","response":integrated_response})
integrated_body=integrated_response.get("response") or {}
assert integrated_response["http_status"]==200 and not integrated_body.get("error")
integrated_result=integrated_body.get("result") or {}
integrated_screen=integrated_result.get("opportunity_screen") or {}
integrated_scope=integrated_result.get("opportunity_research_scope") or {}
assert integrated_result.get("derived_synthesis_status")=="COMPLETED"
assert integrated_screen.get("candidate_universe")==["ITUB4","BBDC4"]
integrated_stock=set(integrated_screen.get("portfolio_stock_universe") or [])
integrated_options=set(integrated_screen.get("portfolio_option_underlying_universe") or [])
integrated_union=set(integrated_screen.get("requested_universe") or [])
expected_union={"ITUB4","BBDC4"}|expected_stock|expected_option_underlyings
assert expected_union==integrated_union, "Active Opportunities lost candidate/stock/option snapshot coverage"
assert len(integrated_screen.get("rows") or [])==len(expected_union)
assert integrated_scope.get("policy_version")=="B3_OPPORTUNITY_RESEARCH_ENRICHMENT_V1"
assert len(integrated_scope.get("context_tickers") or [])<=8
assert expected_stock<=integrated_stock and expected_option_underlyings<=integrated_options
synthesis=integrated_result.get("synthesis") or {}
proposal=integrated_result.get("decision_proposal") or integrated_result.get("proposal") or {}
narrative=next((v for v in (synthesis.get("summary"),proposal.get("thesis"),proposal.get("rationale"),integrated_result.get("summary")) if isinstance(v,str) and v.strip()),None)
assert narrative, "Active Opportunities has no usable senior narrative"
print(json.dumps({"case":"ACTIVE_INTEGRATED_OPPORTUNITIES","http":200,
    "elapsed_ms":integrated_response["elapsed_ms"],"synthesis_status":integrated_result.get("derived_synthesis_status"),
    "candidate_count":len(integrated_screen.get("candidate_universe") or []),
    "portfolio_stock_count":len(integrated_stock),"option_underlying_count":len(integrated_options),
    "requested_universe_count":len(integrated_union),"research_context_count":integrated_scope.get("contextual_research_count"),
    "source_count":len(integrated_body.get("sources") or [])}),flush=True)
print("ACTIVE_BACKEND_CLOSURE=PASS", flush=True)
