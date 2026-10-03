from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
import math
import pytest

from b3_agent.opportunity_screen import StockOpportunityScreenService
from b3_agent.schemas.market import StockMarketData
from b3_agent.schemas.position import PortfolioContext, Position

CUTOFF = datetime(2026,10,3,12,tzinfo=timezone.utc)


def history(ticker, *, scale=1, count=70, volume=1000):
    days, day = [], date(2026,10,2)
    while len(days)<count:
        if day.weekday()<5: days.append(day)
        day -= timedelta(days=1)
    result=[]
    for index, day in enumerate(reversed(days)):
        observed=datetime.combine(day,datetime.min.time(),tzinfo=timezone.utc)
        price=50*math.exp(scale*0.01*(1 if index%2 else -1))
        result.append(StockMarketData(instrument_id=ticker,ticker=ticker,observation_timestamp=observed,available_timestamp=observed,ingested_at=observed,source='fixture',open=price,high=price,low=price,close=price,volume=volume))
    return result


class Providers:
    def __init__(self, records): self.records=records; self.quote_calls=0; self.fund_calls=0
    def get_market_data(self,ticker,start,end): return self.records[ticker]
    def get_current_quote(self,ticker): self.quote_calls+=1; return self.records[ticker][-1]
    def get_financial_data(self,ticker): self.fund_calls+=1; return []


def service(records):
    provider=Providers(records)
    return StockOpportunityScreenService(SimpleNamespace(market_provider=provider,current_quote_provider=provider,fundamentals_provider=provider),target_service=SimpleNamespace(build=lambda ticker,cutoff:{"status":"UNKNOWN_NO_ADMISSIBLE_TARGETS","rows":[]})),provider


def test_lower_observed_risk_ranks_without_valuation_or_personal_outcomes():
    screen,_=service({'ITUB4':history('ITUB4',scale=1),'VALE3':history('VALE3',scale=3)})
    data=screen.build(['VALE3','ITUB4'],objective='LOWEST_REALIZED_VOLATILITY_60D',as_of=CUTOFF)
    rows=data['opportunity_screen']['rows']
    assert [r['ticker'] for r in rows]==['ITUB4','VALE3']
    assert [r['rank'] for r in rows]==[1,2]
    assert all(r['expected_return'] is None and r['portfolio']['held'] is None for r in rows)
    assert data['opportunity_screen']['status']=='RANKED_CONDITIONALLY'


def test_liquidity_direction_and_ties_are_explicit():
    screen,_=service({'ITUB4':history('ITUB4',volume=1000),'VALE3':history('VALE3',volume=2000),'BBAS3':history('BBAS3',volume=2000)})
    rows=screen.build(['ITUB4','VALE3','BBAS3'],objective='HIGHEST_OBSERVED_LIQUIDITY_20D',as_of=CUTOFF)['opportunity_screen']['rows']
    assert [(r['ticker'],r['rank']) for r in rows]==[('BBAS3',1),('VALE3',1),('ITUB4',3)]


def test_pit_filters_future_and_wrong_identity_and_does_not_fetch_current_inputs():
    rows=history('ITUB4')
    future=replace(rows[-1],available_timestamp=CUTOFF+timedelta(days=1),close=9999)
    foreign=replace(rows[-1],ticker='VALE3')
    screen,provider=service({'ITUB4':rows+[future,foreign]})
    data=screen.build(['ITUB4'],objective='LOWEST_REALIZED_VOLATILITY_60D',as_of=CUTOFF)
    assert provider.quote_calls==provider.fund_calls==0
    assert data['opportunity_screen']['rows'][0]['excluded_pit_or_identity_count']==2
    assert data['opportunity_screen']['rows'][0]['history_count']==70
    assert data['opportunity_screen']['rows'][0]['rank'] is None
    assert data['asset_evidence']['ITUB4']['market']['current_quote'] is None


def test_short_and_different_windows_are_not_ranked_as_peers():
    records={'ITUB4':history('ITUB4'),'VALE3':history('VALE3',count=10),'BBAS3':history('BBAS3')[0:-1]}
    screen,_=service(records)
    result=screen.build(list(records),objective='HIGHEST_OBSERVED_LIQUIDITY_20D',as_of=CUTOFF)['opportunity_screen']
    assert result['ranked_count']==0
    rows={r['ticker']:r for r in result['rows']}
    assert 'INSUFFICIENT_OBJECTIVE_SAMPLE' in rows['VALE3']['exclusions']
    assert any('NONCOMPARABLE_OBSERVATION_WINDOW' in r['exclusions'] for r in result['rows'])


def test_portfolio_union_preserves_short_and_outside_classification(monkeypatch):
    portfolio=PortfolioContext(as_of=date(2026,10,2),positions=(Position(position_id='short',ticker='ITUB4',instrument_type='STOCK',quantity=-100),))
    screen,_=service({'ITUB4':history('ITUB4'),'VALE3':history('VALE3')})
    result=screen.build(['VALE3'],include_portfolio=True,portfolio=portfolio)['opportunity_screen']
    rows={r['ticker']:r for r in result['rows']}
    assert rows['ITUB4']['portfolio']['stock_quantity']==-100
    assert rows['ITUB4']['portfolio']['held'] is True
    assert rows['VALE3']['portfolio']['held'] is False
    assert all(r['rank'] is None for r in rows.values())


@pytest.mark.parametrize('objective,tickers', [('invented',['ITUB4']),('COMPARE_ONLY',['WWEGE3']),('COMPARE_ONLY',[f'AAAA{i}' for i in range(21)])])
def test_invalid_objectives_symbols_and_oversized_universe_fail_before_providers(objective,tickers):
    screen,provider=service({})
    with pytest.raises(ValueError): screen.build(tickers,objective=objective)
    assert provider.quote_calls==0


def test_http_deterministic_screen_never_configures_senior(monkeypatch):
    from fastapi.testclient import TestClient
    import b3_agent.server as server
    screen,_=service({'ITUB4':history('ITUB4'),'VALE3':history('VALE3')})
    monkeypatch.setattr('b3_agent.opportunity_screen.StockOpportunityScreenService',lambda:screen)
    monkeypatch.setattr(server,'_configure_runtime',lambda: (_ for _ in ()).throw(AssertionError('senior called')))
    response=TestClient(server.app).post('/orchestrate',json={'task':'Compare explicit assets','ticker':'PETR4','context':{'workspace':'Opportunities','opportunity_assets':['ITUB4','VALE3'],'opportunity_objective':'LOWEST_REALIZED_VOLATILITY_60D','analysis_mode':'deterministic','as_of':CUTOFF.isoformat()}})
    assert response.status_code==200
    data=response.json()
    assert data['result']['telemetry']['llm_calls']==0
    assert set(data['result']['asset_evidence'])=={'ITUB4','VALE3'}
    assert data['result']['opportunity_screen']['ranked_count']==2


def test_current_screen_enriches_economics_and_keeps_observed_rank_separate():
    records={'ITUB4':history('ITUB4'),'BBDC4':history('BBDC4')}
    screen,_=service(records)
    def targets(ticker,cutoff):
        return {'status':'QUALIFIED_OBSERVATIONS','rows':[{'institution':'XP','price_brl':60 if ticker=='ITUB4' else 55,
            'horizon_date':date(2027,12,31),'published_at':CUTOFF-timedelta(days=1),
            'document_id':ticker,'source_url':'fixture'}]}
    screen.target_service=SimpleNamespace(build=targets)
    data=screen.build(list(records),economic_inputs={'budget_brl':1000,'entry_costs_brl':{'ITUB4':0,'BBDC4':0},'target_institution':'XP','target_horizon':'2027-12-31'})
    assert data['economic_target_ranking']['status']=='CONDITIONAL_TARGET_POTENTIAL'
    assert all(r['rank'] is None for r in data['opportunity_screen']['rows'])
    for row in data['opportunity_screen']['rows']:
        evidence=row['economic_evidence']
        assert evidence['quantity']>0 and evidence['expected_return'] is None
        assert evidence['announced_conditional_gross_income_brl'] is None
        assert row['dividends']['collection_status']=='UNSUPPORTED_PROVIDER'
        assert abs(evidence['notional_brl']+evidence['residual_cash_brl']-1000)<1e-7


def test_unsupported_or_incomplete_economic_inputs_fail_before_acquisition():
    screen,provider=service({'ITUB4':history('ITUB4')})
    for inputs in ({'budget_brl':float('nan')},{'entry_costs_brl':{'BBDC4':0}},{'target_institution':'XP'},{'target_institution':'XP','target_horizon':'future'},{'forecast':99}):
        with pytest.raises(ValueError): screen.build(['ITUB4'],economic_inputs=inputs)
    assert provider.quote_calls==0
