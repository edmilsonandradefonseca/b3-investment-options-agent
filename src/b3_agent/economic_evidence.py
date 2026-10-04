"""Explain sourced target potential, announced income and purchase exposure.

Broker target upside is a conditional price-only observation, never expected
return. Announced entitlement is not a forecast or guaranteed personal income.
"""
from datetime import date
from decimal import Decimal, ROUND_FLOOR
from b3_agent.stock_purchase import _number


def economic_evidence(row, *, budget=None, entry_cost=None, portfolio=None):
    spot=_number(row.get('current_price_brl'))
    budget=_number(budget); entry_cost=_number(entry_cost)
    quantity=notional=residual=None
    if spot is not None and spot>0 and budget is not None and budget>0 and entry_cost is not None and 0<=entry_cost<=budget:
        price=Decimal(str(spot)); capital=Decimal(str(budget)); fee=Decimal(str(entry_cost))
        quantity=int(((capital-fee)/price).to_integral_value(rounding=ROUND_FLOOR))
        notional=float(quantity*price); residual=float(capital-fee-quantity*price)
    targets=[]
    # Successive versions remain visible but only the latest publication per
    # institution/horizon is eligible for an explicitly requested comparison.
    for target in row.get('institution_targets',{}).get('rows',[]):
        price=_number(target.get('price_brl'))
        if spot is None or spot<=0 or price is None or price<=0: continue
        targets.append({**target,'price_only_upside_fraction':price/spot-1,
            'price_only_gain_brl':quantity*(price-spot) if quantity is not None else None,
            'net_return':None,'expected_return':None})
    dividends=row.get('dividends',{})
    announced=dividends.get('announced_conditional_gross_per_share_brl')
    past=dividends.get('observed_paid_365d_gross_per_share_brl')
    impact={'status':'UNKNOWN_PORTFOLIO_OR_SIZING','stock_quantity_before':None,
            'stock_quantity_after':None,'cash_after_entry_brl':None,'gross_asset_share_before':None,
            'gross_asset_share_after':None,'related_option_positions':[],
            'snapshot_as_of':portfolio.as_of if portfolio is not None else None}
    if portfolio is not None:
        stocks=[p for p in portfolio.positions if p.ticker.upper()==row['ticker'] and p.instrument_type.upper()=='STOCK']
        before=sum(p.quantity for p in stocks)
        related=[p for p in portfolio.positions if p.instrument_type.upper()=='OPTION' and (p.underlying_ticker or '').upper()==row['ticker']]
        impact.update(stock_quantity_before=before,
            stock_quantity_after=before+quantity if quantity is not None else None,
            related_option_positions=[{'position_id':p.position_id,'quantity':p.quantity,'option_type':p.option_type,
                'strike':p.strike,'expiration_date':p.expiration_date,'contract_multiplier':p.contract_multiplier} for p in related])
        if quantity is not None:
            spend=notional+entry_cost
            impact['status']='CONDITIONAL_PURCHASE_EXPOSURE'
            if portfolio.cash_is_known:
                impact['cash_after_entry_brl']=portfolio.cash-spend
                if spend>portfolio.cash: impact['status']='INSUFFICIENT_RECORDED_CASH'
            if portfolio.cash_is_known and all(_number(p.market_value) is not None for p in portfolio.positions):
                total=sum(abs(p.market_value) for p in portfolio.positions)+portfolio.cash
                prior=sum(p.market_value for p in stocks)
                denominator=total-abs(prior)+abs(prior+notional)-spend
                if total>0: impact['gross_asset_share_before']=abs(prior)/total
                if denominator>0 and impact['status']!='INSUFFICIENT_RECORDED_CASH':
                    impact['gross_asset_share_after']=abs(prior+notional)/denominator
    return {'ticker':row['ticker'],'policy_version':'sourced-economic-evidence-v1',
        'budget_brl':budget,'entry_cost_brl':entry_cost,'quantity':quantity,'notional_brl':notional,'residual_cash_brl':residual,
        'institution_target_potential':targets,
        'announced_conditional_gross_income_brl':quantity*announced if quantity is not None and announced is not None else None,
        'observed_paid_365d_gross_yield_fraction':past/spot if past is not None and spot is not None and spot>0 else None,
        'dividend_coverage':dividends.get('coverage_status','UNKNOWN'),
        'observed_risk':row.get('observed_risk',{}),'portfolio_impact':impact,
        'expected_return':None,'future_dividend_forecast':None,'positive_return_probability':None,
        'limitations':['Target potential excludes dividends, fees and taxes; each institution/date/horizon stays separate.',
            'Observed paid yield is descriptive with unknown coverage; announced income requires timely eligible ownership.',
            'Sizing requires explicit entry costs. Portfolio shares use recorded gross position values plus cash, not NAV or sector diversification.',
            'Portfolio exposure is conditional on funding from recorded cash; related options remain separate and are not netted away.']}


def rank_target_potential(rows, institution, horizon):
    if institution not in {'BTG','XP','SAFRA','ITAU'}: raise ValueError('An explicit supported target institution is required')
    try: date.fromisoformat(horizon)
    except (ValueError,TypeError): raise ValueError('An explicit target horizon date is required') from None
    candidates=[]; excluded=[]
    for row in rows:
        matching=[t for t in row['institution_target_potential'] if t['institution']==institution and str(t['horizon_date'])==horizon]
        if matching:
            newest=max(t['published_at'] for t in matching)
            matching=[t for t in matching if t['published_at']==newest]
        if not matching or len({t['price_brl'] for t in matching})!=1:
            excluded.append(row['ticker']); continue
        target=matching[0]
        candidates.append({'ticker':row['ticker'],'rank':None,'price_only_upside_fraction':target['price_only_upside_fraction'],
            'document_id':target['document_id'],'source_url':target['source_url'],'published_at':target['published_at']})
    candidates.sort(key=lambda r:(-r['price_only_upside_fraction'],r['ticker']))
    if len(candidates)>=2:
        previous=None; rank=None
        for i,row in enumerate(candidates,1):
            if row['price_only_upside_fraction']!=previous: rank=i
            row['rank']=rank; previous=row['price_only_upside_fraction']
    return {'objective':'HIGHEST_INSTITUTION_TARGET_PRICE_POTENTIAL','institution':institution,'horizon_date':horizon,
        'status':'CONDITIONAL_TARGET_POTENTIAL' if len(candidates)>=2 else 'INSUFFICIENT_COMPARABLE_TARGETS',
        'rows':candidates,'excluded_tickers':excluded,'expected_return':None,
        'limitations':['Same institution and target horizon required; report dates remain visible and may differ.',
            'Price-only broker opinions cannot establish total return, probability, suitability or the best overall purchase.']}
