"""Read-only active HTTP acceptance of Strategy Lab and Market Intelligence."""
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

def parse_aware_timestamp(value, label):
    assert isinstance(value, str) and value.strip(), f'{label} timestamp missing'
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    assert parsed.tzinfo is not None and parsed.utcoffset() is not None, f'{label} timestamp must include timezone'
    return parsed.astimezone(timezone.utc)

started=monotonic()
response=client.post('/orchestrate',json={'task':'Explique os sinais técnicos, os eventos elegíveis, os fundamentos e a exposição existente em PETR4. Diferencie fatos, interpretação e lacunas; não consulte cadeias de opções nem invente valuation.', 'ticker':'PETR4','context':{'workspace':'Market Intelligence','selected_ticker':'PETR4','asset_view':True,'research_mode':'stored_first'}})
require_http_ok(response, 'MI-active-http')
payload=response.json(); result=payload['result']
assert not payload.get('error')
assert result.get('derived_synthesis_status') == 'COMPLETED'
workspace = result['workspace_intelligence']
market_context = workspace['market_context']
market=market_context['tickers']['PETR4']
asset_evidence=market.get('asset_evidence')
assert isinstance(asset_evidence, dict), 'MI must carry deterministic PETR4 evidence'
asset_market=asset_evidence.get('market') or {}
quote=market.get('current_quote')
assert isinstance(quote, dict), 'MI must include a current PETR4 quote or explicitly fail'
assert quote.get('ticker') == 'PETR4' and quote.get('currency') == 'BRL'
assert isinstance(quote.get('close'), (int, float)) and quote['close'] > 0
quote_time=parse_aware_timestamp(quote.get('observation_timestamp'), 'current quote')
quote_available=parse_aware_timestamp(quote.get('available_timestamp'), 'current quote availability')
now=datetime.now(timezone.utc)
assert quote_time <= now and quote_available <= now, 'MI quote cannot come from the future'
quote_age_hours=(now-quote_time).total_seconds()/3600
assert quote_age_hours <= 24, f'MI current quote is not fresh enough ({quote_age_hours:.1f} hours)'
history_count=asset_market.get('history_count')
assert isinstance(history_count, int) and history_count >= 60, 'MI needs at least 60 historical observations'
history_end=parse_aware_timestamp(asset_market.get('history_end'), 'history end')
assert history_end <= now and (now-history_end).days <= 7, 'MI history must have a recent, point-in-time eligible tail'
history_1m=(asset_market.get('historical_returns') or {}).get('1M') or {}
assert history_1m.get('status') == 'AVAILABLE' and history_1m.get('return_fraction') is not None
assert 'institution_targets' in market and 'issuer_dividends' in market
target_status=market['institution_targets'].get('status')
dividend_status=market['issuer_dividends'].get('collection_status')
assert isinstance(target_status, str) and target_status
assert isinstance(dividend_status, str) and dividend_status
research_events=market.get('research_events') or []
for event in research_events:
    assert event.get('source_ref') and event.get('published_at'), 'Every displayed research event needs source and publication date'
acquisition=market.get('research_acquisition') or {}
assert acquisition.get('coverage') == 'BOUNDED_RESEARCH_ONLY_NOT_EXHAUSTIVE'
proposal=result.get('proposal') or result.get('decision_proposal') or {}
assert proposal.get('thesis') and proposal.get('rationale')
print(json.dumps({'instance':'ACTIVE HTTP systemd','case':'MI-02 current PETR4 quote and sourced history','status':'PASS','quote_source':quote.get('source'),'quote_age_hours':round(quote_age_hours,2),'history_count':history_count,'history_end':asset_market.get('history_end'),'history_1m_status':history_1m.get('status')}),flush=True)
print(json.dumps({'instance':'ACTIVE HTTP systemd','case':'MI-02/04/05 targets, dividends, research provenance and synthesis','status':'PASS','target_status':target_status,'dividend_collection_status':dividend_status,'research_event_count':len(research_events),'research_coverage':acquisition.get('coverage'),'elapsed_s':round(monotonic()-started,2)}),flush=True)
