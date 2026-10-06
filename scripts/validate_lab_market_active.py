"""Acceptance of Lab and MI on the running API; no service mutation."""
import json
from time import monotonic
import httpx
client = httpx.Client(base_url="http://127.0.0.1:8000", timeout=210)
assert client.get("/health").status_code == 200
def require_http_ok(response, stage):
    if response.status_code != 200:
        try:
            detail = str(response.json().get('detail', ''))
        except ValueError:
            detail = ''
        hints = [word for word in ('timed out', 'Gateway', 'connection', 'JSON', 'schema', 'assessment', 'context', 'token', 'rate limit', 'payload') if word.lower() in detail.lower()]
        print(json.dumps({'case':stage,'http_status':response.status_code,'error_chars':len(detail),'failure_hints':hints}),flush=True)
    assert response.status_code == 200

request={'task':'Tenho R$ 10 mil. Comprar ITUB4 ou BBDC4?','ticker':None,'context':{'workspace':'Strategy Lab','research_mode':'stored_only','analysis_mode':'deterministic'}}
started=monotonic()
response=client.post('/orchestrate',json=request)
require_http_ok(response, 'active-http')
result=response.json()
assert not result.get('error')
rows=result['result']['stock_purchase_comparison']['rows']
assert {r['ticker'] for r in rows}=={'ITUB4','BBDC4'}
from datetime import datetime, timezone
purchase = result['result']['stock_purchase_comparison']
common = purchase['common_normalized_history']
assert common['status'] == 'AVAILABLE' and len(common['rows']) >= 60
for row in rows:
    gross = row['economic_evidence']['gross_purchase_before_costs']
    assert gross['quantity'] > 0
    assert abs(gross['notional_brl'] + gross['residual_cash_brl'] - row['capital_required_brl']) < 1e-7
    assert row['economic_evidence']['quantity'] is None, 'Unknown costs cannot become net sizing'
    tail = datetime.fromisoformat(str(row['historical_returns']['1W']['end_at']).replace('Z', '+00:00'))
    assert (datetime.now(timezone.utc) - tail).days <= 7, 'Freshly fetched history lost at pre-acquisition cutoff'
print(json.dumps({'case':'LAB-03/05 history and gross sizing','status':'PASS','common_sessions':len(common['rows']),'basis':common['price_basis']}),flush=True)
print(json.dumps({'instance':'ACTIVE HTTP systemd','case':'LAB-01 natural budget' ,'status':'PASS','rows':len(rows),'elapsed_s':round(monotonic()-started,2)}),flush=True)
request['context'].pop('analysis_mode')
request['context']['research_mode']='stored_first'
started=monotonic()
response=client.post('/orchestrate',json=request)
require_http_ok(response, 'active-http')
payload=response.json(); result=payload['result']
assert not payload.get('error')
proposal=result.get('proposal') or result.get('decision_proposal') or {}
assert proposal.get('thesis') and proposal.get('rationale'), 'Missing central senior narrative'
assert len(result['stock_purchase_comparison']['rows'])==2
print(json.dumps({'instance':'ACTIVE HTTP systemd','case':'LAB-02 senior plus canonical comparison','status':'PASS','thesis_chars':len(proposal['thesis']),'rationale_chars':len(proposal['rationale']),'elapsed_s':round(monotonic()-started,2)}),flush=True)

started=monotonic()
response=client.post('/orchestrate',json={'task':'Explique os sinais técnicos, os eventos elegíveis, os fundamentos e a exposição existente em PETR4. Diferencie fatos, interpretação e lacunas; não consulte cadeias de opções nem invente valuation.', 'ticker':'PETR4','context':{'workspace':'Market Intelligence','selected_ticker':'PETR4','asset_view':True,'research_mode':'stored_first'}})
require_http_ok(response, 'MI-active-http')
payload=response.json(); result=payload['result']
assert not payload.get('error')
assert result.get('derived_synthesis_status') == 'COMPLETED'
market=result['workspace_intelligence']['market_context']['tickers']['PETR4']
assert 'institution_targets' in market and 'issuer_dividends' in market
proposal=result.get('proposal') or result.get('decision_proposal') or {}
assert proposal.get('thesis') and proposal.get('rationale')
print(json.dumps({'instance':'ACTIVE HTTP systemd','case':'MI-02/04/05 senior and stored evidence','status':'PASS','target_status':market['institution_targets'].get('status'),'dividend_collection_status':market['issuer_dividends'].get('collection_status'),'elapsed_s':round(monotonic()-started,2)}),flush=True)
