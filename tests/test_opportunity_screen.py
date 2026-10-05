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
    return StockOpportunityScreenService(SimpleNamespace(market_provider=provider,current_quote_provider=provider,fundamentals_provider=provider),dividend_service=SimpleNamespace(build=lambda ticker,cutoff:{"status":"NO_STORED_SNAPSHOT","records":[]}),target_service=SimpleNamespace(build=lambda ticker,cutoff:{"status":"UNKNOWN_NO_ADMISSIBLE_TARGETS","rows":[]})),provider


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


@pytest.mark.parametrize('objective,tickers', [('invented',['ITUB4']),('COMPARE_ONLY',['WWEGE3'])])
def test_invalid_objectives_and_symbols_fail_before_providers(objective,tickers):
    screen,provider=service({})
    with pytest.raises(ValueError): screen.build(tickers,objective=objective)
    assert provider.quote_calls==0


def test_complete_candidate_and_portfolio_union_has_no_twenty_asset_ceiling():
    candidates=[f'AAAA{index}' for index in range(1,22)]
    records={ticker:history(ticker) for ticker in candidates}
    portfolio=PortfolioContext(as_of=date(2026,10,2),positions=(
        Position(position_id='held-1',ticker='BBBB1',instrument_type='STOCK',quantity=100),
        Position(position_id='held-2',ticker='CCCC1',instrument_type='STOCK',quantity=50),
    ))
    records.update({'BBBB1':history('BBBB1'),'CCCC1':history('CCCC1')})
    screen,_=service(records)

    result=screen.build(candidates,include_portfolio=True,portfolio=portfolio)

    requested=result['opportunity_screen']['requested_universe']
    assert len(requested)==23
    assert requested[:len(candidates)]==candidates
    assert set(requested[-2:])=={'BBBB1','CCCC1'}
    assert len(result['opportunity_screen']['rows'])==23
    assert result['opportunity_screen']['portfolio_scope']['status']=='INCLUDED'


def test_missing_portfolio_keeps_candidate_analysis_and_marks_portfolio_gap(monkeypatch):
    monkeypatch.setattr('b3_agent.opportunity_screen.load_active_snapshots',lambda *_:{})
    screen,_=service({'ITUB4':history('ITUB4')})

    result=screen.build(['ITUB4'],include_portfolio=True,portfolio=None)

    assert result['opportunity_screen']['requested_universe']==['ITUB4']
    assert result['opportunity_screen']['portfolio_scope']['status']=='UNAVAILABLE'
    assert 'CURRENT_PORTFOLIO_UNAVAILABLE' in result['opportunity_screen']['limitations'][-1]
    assert result['opportunity_screen']['rows'][0]['portfolio']['held'] is None


def test_opportunity_context_exposes_open_option_and_covered_call_exposure():
    records={'AAAA1':history('AAAA1')}
    portfolio=PortfolioContext(as_of=date(2026,10,2),positions=(
        Position(position_id='stock',ticker='AAAA1',instrument_type='STOCK',quantity=50),
        Position(position_id='put',ticker='AAAA1P2610',instrument_type='OPTION',quantity=-2,
            strike=10,expiration_date=date(2026,10,16),option_type='PUT',underlying_ticker='AAAA1',contract_multiplier=100),
        Position(position_id='call',ticker='AAAA1C2610',instrument_type='OPTION',quantity=-1,
            strike=15,expiration_date=date(2026,10,16),option_type='CALL',underlying_ticker='AAAA1',contract_multiplier=100),
    ))
    screen,_=service(records)

    row=screen.build(['AAAA1'],include_portfolio=True,portfolio=portfolio)['opportunity_screen']['rows'][0]

    assert row['portfolio']['open_option_count']==2
    assert row['portfolio']['short_put_assignment_capital_brl']==2000
    assert row['portfolio']['short_call_units']==100
    assert row['portfolio']['covered_call_units']==50
    assert row['portfolio']['covered_call_status']=='PARTIALLY_COVERED'
    assert {item['option_type'] for item in row['portfolio']['open_options']}=={'PUT','CALL'}


def test_option_only_underlying_is_context_and_never_ranked_as_discovery():
    records={ticker:history(ticker) for ticker in ('ITUB4','BBDC4','PETR4')}
    portfolio=PortfolioContext(as_of=date(2026,10,2),positions=(
        Position(position_id='put',ticker='PETRK300',instrument_type='OPTION',quantity=-1,
            strike=30,expiration_date=date(2026,10,16),option_type='PUT',underlying_ticker='PETR4',contract_multiplier=100),
    ))
    screen,_=service(records)

    result=screen.build(['ITUB4','BBDC4'],objective='LOWEST_REALIZED_VOLATILITY_60D',
        include_portfolio=True,portfolio=portfolio)

    output=result['opportunity_screen']
    assert output['portfolio_option_underlying_universe']==['PETR4']
    context_row=next(row for row in output['rows'] if row['ticker']=='PETR4')
    assert context_row['scope_role']=='OPTION_UNDERLYING_CONTEXT'
    assert context_row['discovery_eligible'] is False
    assert context_row['rank'] is None
    assert context_row['portfolio']['open_option_count']==1
    assert output['ranked_count']==2


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
        assert row['dividends']['collection_status']=='NO_STORED_SNAPSHOT'
        assert abs(evidence['notional_brl']+evidence['residual_cash_brl']-1000)<1e-7


def test_unsupported_or_incomplete_economic_inputs_fail_before_acquisition():
    screen,provider=service({'ITUB4':history('ITUB4')})
    for inputs in ({'budget_brl':float('nan')},{'entry_costs_brl':{'BBDC4':0}},{'target_institution':'XP'},{'target_institution':'XP','target_horizon':'future'},{'forecast':99}):
        with pytest.raises(ValueError): screen.build(['ITUB4'],economic_inputs=inputs)
    assert provider.quote_calls==0


def test_materiality_emits_review_candidate_and_keeps_observed_rank_separate():
    screen,_=service({'ITUB4':history('ITUB4'),'BBDC4':history('BBDC4')})
    def targets(ticker,cutoff):
        target_price=60 if ticker=='ITUB4' else 54
        return {'status':'QUALIFIED_OBSERVATIONS','rows':[{'institution':'XP','price_brl':target_price,
            'horizon_date':date(2027,12,31),'published_at':CUTOFF-timedelta(days=1),
            'document_id':ticker,'source_url':'https://example.test/'+ticker}]}
    screen.target_service=SimpleNamespace(build=targets)
    result=screen.build(['ITUB4','BBDC4'])
    opportunity=result['opportunity_screen']
    assert opportunity['materiality_policy_version']=='B3_STOCK_MATERIALITY_TARGET_REVIEW_V1'
    assert opportunity['materiality_status']=='MATERIAL_REVIEW_ITEMS_FOUND'
    assert [item['ticker'] for item in opportunity['material_candidates']]==['ITUB4']
    assert opportunity['material_candidates'][0]['category']=='POTENCIAL_ENTRADA_PARA_REVISAO'
    assert opportunity['material_candidates'][0]['conditional_price_only_upside_fraction']>=0.15
    assert opportunity['monitor_candidates'][0]['ticker']=='BBDC4'
    assert all(row['rank'] is None for row in opportunity['rows'])
    assert all(row['economic_evidence']['expected_return'] is None for row in opportunity['rows'])


def test_materiality_distinguishes_unavailable_targets_from_valid_no_target_review():
    screen,_=service({'ITUB4':history('ITUB4')})
    screen.target_service=SimpleNamespace(build=lambda ticker,cutoff:{
        'status':'STORE_UNAVAILABLE','rows':[]})
    result=screen.build(['ITUB4'])
    assert result['opportunity_screen']['materiality_status']=='EVIDENCE_INCOMPLETE'
    assert result['opportunity_screen']['material_candidates']==[]
    assert result['opportunity_screen']['incomplete_materiality_count']==1
    row=result['opportunity_screen']['rows'][0]
    assert row['materiality']['status']=='INCOMPLETE'
    assert 'falhou' in row['materiality']['reason']
