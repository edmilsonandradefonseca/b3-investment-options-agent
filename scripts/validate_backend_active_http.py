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
assert all(row["fundamental_metrics"] for row in rows), "Expected previously validated available fundamentals"
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
print("ACTIVE_BACKEND_CLOSURE=PASS", flush=True)
