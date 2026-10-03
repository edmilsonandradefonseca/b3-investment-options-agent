from datetime import date,datetime,timezone
from b3_agent.economic_evidence import economic_evidence,rank_target_potential
from b3_agent.schemas.position import Position,PortfolioContext

def row(ticker='ITUB4',target=40):
    return {'ticker':ticker,'current_price_brl':30.,'dividends':{'announced_conditional_gross_per_share_brl':1.,'observed_paid_365d_gross_per_share_brl':2.,'coverage_status':'UNKNOWN'},'institution_targets':{'rows':[{'institution':'XP','price_brl':target,'horizon_date':date(2027,12,31),'published_at':datetime(2026,8,6,tzinfo=timezone.utc),'document_id':ticker,'source_url':'fixture'}]}}

def test_sourced_potential_income_and_sizing_preserve_forecast_unknown():
    result=economic_evidence(row(),budget=1000,entry_cost=10)
    assert result['quantity']==33 and result['residual_cash_brl']==0
    assert result['announced_conditional_gross_income_brl']==33
    assert result['institution_target_potential'][0]['price_only_gain_brl']==330
    assert result['expected_return'] is result['future_dividend_forecast'] is None
    assert economic_evidence(row(),budget=1000)['quantity'] is None

def test_portfolio_cash_and_signed_short_purchase_exposure():
    portfolio=PortfolioContext(as_of=date(2026,10,3),cash=1000,positions=(Position(position_id='a',ticker='ITUB4',instrument_type='STOCK',quantity=-10,market_value=-300),))
    result=economic_evidence(row(),budget=1000,entry_cost=10,portfolio=portfolio)['portfolio_impact']
    assert result['stock_quantity_after']==23 and result['cash_after_entry_brl']==0
    assert abs(result['gross_asset_share_after']-1)<1e-10
    missing=PortfolioContext(as_of=portfolio.as_of,cash=1000,positions=(Position(position_id='a',ticker='ITUB4',instrument_type='STOCK',quantity=10),))
    assert economic_evidence(row(),budget=1000,entry_cost=10,portfolio=missing)['portfolio_impact']['gross_asset_share_after'] is None
    assert economic_evidence(row(),budget=2000,entry_cost=0,portfolio=portfolio)['portfolio_impact']['status']=='INSUFFICIENT_RECORDED_CASH'

def test_rank_requires_same_institution_horizon_and_two_complete_assets():
    rows=[economic_evidence(row()),economic_evidence(row('BBDC4',35))]
    ranked=rank_target_potential(rows,'XP','2027-12-31')
    assert [r['rank'] for r in ranked['rows']]==[1,2]
    assert rank_target_potential(rows,'BTG','2027-12-31')['status']=='INSUFFICIENT_COMPARABLE_TARGETS'
    assert rank_target_potential(rows,'XP','2026-12-31')['rows']==[]
