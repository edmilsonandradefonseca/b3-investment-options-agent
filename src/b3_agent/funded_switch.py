"""Decision-time financing of an explicit stock switch; no execution or forecast."""
from dataclasses import asdict
from decimal import Decimal, ROUND_FLOOR
from b3_agent.config import settings
from b3_agent.portfolio.snapshot import load_active_snapshots
from b3_agent.opportunity_screen import StockOpportunityScreenService
from b3_agent.schemas.strategy_comparison import StrategyAlternative
from b3_agent.strategy_comparison import StrategyComparisonEngine


def build_funded_switch(assets, inputs, *, screen_service=None, portfolio=None):
    if len(assets) != 2 or assets[0] == assets[1]:
        raise ValueError('A funded switch requires two distinct stock assets')
    quantity = inputs.get('quantity')
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        raise ValueError('Sale quantity must be a positive integer number of shares')
    def money(name):
        raw = inputs.get(name)
        if raw is None: return None
        if isinstance(raw, bool): raise ValueError('Costs must be finite non-negative BRL amounts')
        try: value = Decimal(str(raw))
        except Exception as exc: raise ValueError('Invalid cost amount') from exc
        if not value.is_finite() or value < 0: raise ValueError('Costs must be finite non-negative BRL amounts')
        return value
    fees, taxes = money('fees_brl'), money('taxes_brl')
    if portfolio is None:
        portfolio = load_active_snapshots(settings.data_dir).get('portfolio_context')
    evidence = (screen_service or StockOpportunityScreenService()).build(assets, portfolio=portfolio)
    packs = evidence['asset_evidence']; source, target = (packs[symbol] for symbol in assets)
    held = source['portfolio']['stock_quantity']
    if held is None or held < quantity:
        raise ValueError('Admissible long stock holdings must cover the explicit sale quantity')
    quotes = [pack['market'].get('current_quote') for pack in (source,target)]
    if any(not quote for quote in quotes):
        raise ValueError('Admissible current quotes for both stocks are required')
    cutoff = evidence['as_of']
    if any((cutoff.date()-quote['observation_timestamp'].date()).days > 7 for quote in quotes):
        raise ValueError('Current quotes are too old for funded switching')
    prices = [Decimal(str(quote['close'])) for quote in quotes]
    gross = prices[0]*quantity
    net = gross-fees-taxes if fees is not None and taxes is not None else None
    if net is not None and net < 0: raise ValueError('Declared costs exceed sale proceeds')
    buy_quantity = int((net/prices[1]).to_integral_value(rounding=ROUND_FLOOR)) if net is not None else None
    purchase = prices[1]*buy_quantity if buy_quantity is not None else None
    residual = net-purchase if net is not None else None
    related_options = bool(portfolio and any(position.instrument_type.upper() == 'OPTION' and (position.underlying_ticker or '').upper() in assets for position in portfolio.positions))
    facts = {'policy_version':'funded-stock-switch-v1','status':'COSTS_UNKNOWN' if net is None else 'MODELED_WITH_OPTION_RESTRICTIONS' if related_options else 'MODELED',
        'sell_ticker':assets[0],'buy_ticker':assets[1],'sell_quantity':quantity,'buy_quantity':buy_quantity,
        'sell_price_brl':float(prices[0]),'buy_price_brl':float(prices[1]),'gross_sale_proceeds_brl':float(gross),
        'fees_brl':float(fees) if fees is not None else None,'taxes_brl':float(taxes) if taxes is not None else None,
        'net_sale_proceeds_brl':float(net) if net is not None else None,'purchase_notional_brl':float(purchase) if purchase is not None else None,
        'residual_cash_brl':float(residual) if residual is not None else None,
        'remaining_source_stock_quantity':held-quantity,'target_stock_quantity_before':target['portfolio']['stock_quantity'],
        'related_option_positions_present':related_options,'quote_observed_at':[quote['observation_timestamp'] for quote in quotes],
        'expected_return':None,'ranking':'NOT_APPLIED','execution_authorized':False,
        'limitations':['Prices are indicative provider marks, not executable bid/ask quotes; fills and slippage remain UNKNOWN.',
            'Fees and taxes are explicit scenario amounts, not automatically estimated tax liability; missing costs block net sizing.',
            'Integer shares use a one-share modeling unit; exchange order rules, lot liquidity and executable sizing are not asserted.',
            'Related option obligations are not netted or released by selling shares; coverage and collateral consequences require a separate canonical analysis.',
            'Dividends, targets, future returns and financing yield remain UNKNOWN; no winner or investment recommendation is inferred.']}
    sources = tuple(evidence['source_refs']); refs = tuple('funded_switch:'+symbol for symbol in assets)
    alternatives = [StrategyAlternative(alternative_id='FUNDED-HOLD-'+assets[0],label='Manter as ações selecionadas de '+assets[0],action_type='HOLD',subject_id=assets[0],as_of=cutoff,capital_required=0,assumptions={'selected_quantity':quantity,'decision_time_mark_brl':float(gross)},source_refs=sources,evidence_refs=refs,quality_status='WARNING'),
        StrategyAlternative(alternative_id='FUNDED-SWITCH-'+assets[0]+'-'+assets[1],label='Vender '+assets[0]+' para financiar '+assets[1],action_type='FUNDED_STOCK_SWITCH',subject_id=assets[1],as_of=cutoff,capital_required=None if net is None else 0,assumptions=facts,source_refs=sources,evidence_refs=refs,quality_status='WARNING')]
    return {'as_of':cutoff,'funded_switch':facts,'strategy_comparison':asdict(StrategyComparisonEngine().compare(*alternatives)), 'asset_evidence':packs,'source_refs':list(sources),'limitations':facts['limitations']}
