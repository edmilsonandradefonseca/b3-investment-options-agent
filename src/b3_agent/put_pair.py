"""Explicit two-PUT tradeoffs using canonical per-contract evidence."""
import math
from datetime import datetime
from b3_agent.strategy_live import _put_model_probabilities, _normalize_exercise_style

OBJECTIVES = {'COMPARE_ONLY':None,'LOWEST_MODEL_EXPIRY_ITM':'expiry_itm_probability','HIGHEST_GROSS_PREMIUM_PER_CAPITAL_30D':'gross_premium_per_capital_30d_pct'}


def put_pair_payload(alternatives, evidence, packs, cutoff, objective='COMPARE_ONLY'):
    if objective not in OBJECTIVES: raise ValueError('Unsupported two-PUT objective')
    rows=[]
    for alternative in alternatives:
        item=evidence[alternative.subject_id]; contract=item['contract']; quote=item['current_quote']
        pack=next(pack for pack in packs if pack.ticker==item['underlying_ticker'])
        underlying=pack.market.get('current_quote')
        if underlying:
            observed=underlying.get('observation_timestamp')
            available=underlying.get('available_timestamp')
            if isinstance(observed,str):
                observed=datetime.fromisoformat(observed.replace('Z','+00:00'))
            if isinstance(available,str):
                available=datetime.fromisoformat(available.replace('Z','+00:00'))
            price=underlying.get('close')
            if (str(underlying.get('ticker') or '').upper()!=pack.ticker
                    or underlying.get('currency')!='BRL'
                    or not underlying.get('source')
                    or underlying.get('quality_status') in {'REJECTED','INVALID'}
                    or not isinstance(observed,datetime) or not isinstance(available,datetime)
                    or observed>cutoff or available>cutoff
                    or (cutoff.date()-observed.date()).days>7
                    or not isinstance(price,(int,float)) or not math.isfinite(float(price)) or price<=0):
                underlying=None
        spot=underlying.get('close') if underlying else None
        expiry=contract['expiration_date']; days=(expiry-cutoff.date()).days
        strike=float(contract['strike']); multiplier=float(contract['contract_multiplier']); bid=float(quote['bid'])
        probability=_put_model_probabilities(spot=spot,strike=strike,volatility=quote.get('implied_volatility'),days=days)
        collateral=strike*multiplier; premium=bid*multiplier
        style=_normalize_exercise_style(str(contract.get('exercise_style') or ''))
        rows.append({'alternative_id':alternative.alternative_id,'option_id':alternative.subject_id,'underlying_ticker':pack.ticker,
            'expiration_date':expiry,'days_to_expiration':days,'underlying_price':spot,'strike':strike,
            'downside_to_strike_fraction':(spot-strike)/spot if spot else None,
            'breakeven_cushion_fraction':(spot-(strike-bid))/spot if spot else None,'bid':bid,'ask':quote.get('ask'),'volume':quote.get('volume'),'open_interest':quote.get('open_interest'),
            'contract_multiplier':multiplier,'premium_total_one_contract_brl':premium,'capital_required_one_contract_brl':collateral,
            'maximum_loss_one_contract_before_costs_brl':(strike-bid)*multiplier,'breakeven_price':strike-bid,
            'gross_premium_per_capital_pct':premium/collateral*100,
            'gross_premium_per_capital_30d_pct':premium/collateral*100*30/days,
            'probability_estimates':{**probability,'calibration_status':'NOT_CALIBRATED','not_assignment_probability':True},
            'expiry_itm_probability':probability['expiry_itm_probability'],'touch_probability':probability['touch_probability'],
            'early_assignment_status':'NOT_APPLICABLE_BY_PROVIDER_REPORTED_EUROPEAN_STYLE' if style=='EUROPEAN' else 'UNKNOWN',
            'exercise_style':style or 'UNKNOWN','costs_status':'UNKNOWN','net_expected_return':None,'personal_assignment_frequency':None,
            'marketability':item['marketability'],'quote_observed_at':quote['observation_timestamp'],'quote_available_at':quote['available_timestamp'],
            'source_refs':list(alternative.source_refs),'evidence_refs':list(alternative.evidence_refs),'rank':None})
    metric=OBJECTIVES[objective]; ranking='NOT_REQUESTED'
    if metric:
        values=[row[metric] for row in rows]
        if all(isinstance(value,(int,float)) and math.isfinite(value) for value in values):
            if math.isclose(values[0],values[1],rel_tol=1e-9,abs_tol=1e-12):
                ranking='TIE';rows[0]['rank']=rows[1]['rank']=1
            else:
                winner=0 if (values[0]<values[1] if objective=='LOWEST_MODEL_EXPIRY_ITM' else values[0]>values[1]) else 1
                ranking='CONDITIONAL_OBJECTIVE_ONLY';rows[winner]['rank']=1;rows[1-winner]['rank']=2
        else: ranking='UNKNOWN_OBJECTIVE_INPUTS'
    return {'policy_version':'two-put-tradeoffs-v1','objective':objective,'ranking':ranking,'rows':rows,
        'different_expiries':rows[0]['expiration_date']!=rows[1]['expiration_date'],
        'limitations':['Each risk estimate uses its own expiry. Different expiry risks are different exposure horizons, not equal-period probabilities.',
            'Expiry ITM and touch are uncalibrated zero-rate/carry lognormal proxies, not verified assignment probabilities or expected return.',
            '30-day gross premium normalization is simple arithmetic; it assumes neither reinvestment nor repeated achievable trades.',
            'Price distance to strike/break-even is an observed cushion, not a probability; negative values mean the reference price is already below that threshold.',
            'Costs, taxes, early assignment behavior and personal eligible exercise frequency remain UNKNOWN.',
            'One contract per alternative uses the provider multiplier; this does not imply equal capital, portfolio margin or actual execution.',
            'Bid, volume and open interest are provider indications; fill size, stale quotes and liquidity constraints require human review.',
            'Only the explicitly selected metric can conditionally order the alternatives; it is not an overall investment winner.']}
