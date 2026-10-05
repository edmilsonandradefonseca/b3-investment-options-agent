"""Objective-specific stock screening; observed risk/liquidity are not valuation."""
from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import math

from b3_agent.config import settings
from b3_agent.portfolio.snapshot import load_active_snapshots
from b3_agent.quant_engine import compute_quant_features
from b3_agent.schemas.position import PortfolioContext
from b3_agent.strategy_live import AssetEvidencePack, StrategyEvidenceService, _validated_equity_ticker

POLICY = 'B3_OBSERVED_STOCK_SCREEN_V1'
MAX_CONCURRENT_ASSETS = 4
OBJECTIVES = {
    'COMPARE_ONLY': (None, None, 0),
    'LOWEST_REALIZED_VOLATILITY_60D': ('volatility_60d', 'ascending', 61),
    'HIGHEST_OBSERVED_LIQUIDITY_20D': ('average_dollar_volume_20d', 'descending', 20),
}


def _admissible(record, ticker, cutoff):
    return (
        record.ticker.upper() == ticker
        and record.observation_timestamp.tzinfo is not None
        and record.available_timestamp.tzinfo is not None
        and record.observation_timestamp <= cutoff
        and record.available_timestamp <= cutoff
        and record.quality_status not in {'REJECTED', 'INVALID'}
        and bool(record.source)
    )


class StockOpportunityScreenService:
    def __init__(self, evidence_service=None, target_service=None, dividend_service=None):
        self.evidence = evidence_service or StrategyEvidenceService()
        self.target_service = target_service
        self.dividend_service = dividend_service

    def build(self, tickers, *, objective='COMPARE_ONLY', include_portfolio=False,
              as_of=None, portfolio=None, economic_inputs=None):
        if objective not in OBJECTIVES:
            raise ValueError('Unsupported opportunity objective')
        inputs = economic_inputs or {}
        if not isinstance(inputs, dict) or set(inputs)-{'budget_brl','entry_costs_brl','target_institution','target_horizon'}:
            raise ValueError('Unsupported Opportunity economic inputs')
        from b3_agent.stock_purchase import _number
        budget=inputs.get('budget_brl')
        costs=inputs.get('entry_costs_brl',{})
        if budget is not None and (_number(budget) is None or budget<=0): raise ValueError('Budget must be finite and positive')
        if not isinstance(costs,dict) or any(_number(v) is None or v<0 for v in costs.values()): raise ValueError('Entry costs must be finite and nonnegative')
        if ('target_institution' in inputs) != ('target_horizon' in inputs): raise ValueError('Target institution and horizon are jointly required')
        historical = as_of is not None
        if isinstance(as_of, str):
            as_of = datetime.fromisoformat(as_of.replace('Z', '+00:00'))
        if as_of is not None and (not isinstance(as_of, datetime) or as_of.tzinfo is None):
            raise ValueError('Screen as_of must be timezone-aware')
        if portfolio is None:
            try:
                portfolio = load_active_snapshots(settings.data_dir).get('portfolio_context')
            except (OSError, RuntimeError, ValueError):
                portfolio = None
        if not isinstance(portfolio, PortfolioContext) or portfolio.quality_status == 'REJECTED':
            portfolio = None
        # Current snapshots have no proven historical availability owner.
        if historical or (portfolio is not None and portfolio.as_of > (as_of or datetime.now(timezone.utc)).date()):
            portfolio = None
        candidates = list(dict.fromkeys(_validated_equity_ticker(t) for t in tickers))
        portfolio_stock_tickers = []
        portfolio_option_underlying_tickers = []
        unresolved_stock_position_count = 0
        unresolved_option_underlying_count = 0

        def canonical_position_ticker(position):
            if position.instrument_type.upper() == 'OPTION':
                raw = position.underlying_ticker
                if not raw:
                    return None
            else:
                raw = position.ticker
            try:
                return _validated_equity_ticker(raw)
            except (TypeError, ValueError):
                return None

        if portfolio is not None and include_portfolio:
            for position in portfolio.positions:
                instrument_type = position.instrument_type.upper()
                if instrument_type == 'STOCK':
                    ticker = canonical_position_ticker(position)
                    if ticker is None:
                        unresolved_stock_position_count += 1
                    else:
                        portfolio_stock_tickers.append(ticker)
                elif instrument_type == 'OPTION':
                    ticker = canonical_position_ticker(position)
                    if ticker is None:
                        unresolved_option_underlying_count += 1
                    else:
                        portfolio_option_underlying_tickers.append(ticker)
            portfolio_stock_tickers = list(dict.fromkeys(portfolio_stock_tickers))
            portfolio_option_underlying_tickers = list(dict.fromkeys(portfolio_option_underlying_tickers))
        universe = list(candidates)
        if include_portfolio and portfolio is not None:
            universe.extend(portfolio_stock_tickers)
            universe.extend(portfolio_option_underlying_tickers)
            universe = list(dict.fromkeys(universe))
        if not universe:
            raise ValueError('Select at least one candidate asset or include a non-empty equity portfolio')
        if set(costs)-set(universe): raise ValueError('Entry cost asset mismatch')
        if 'target_institution' in inputs:
            from b3_agent.economic_evidence import rank_target_potential
            rank_target_potential([],inputs['target_institution'],inputs['target_horizon'])
        requested_at = as_of or datetime.now(timezone.utc)
        def acquire(ticker):
            errors = []
            records, quote, fundamentals = (), None, ()
            try:
                records = tuple(self.evidence.market_provider.get_market_data(ticker, requested_at.date()-timedelta(days=120), requested_at.date()))
            except (OSError, RuntimeError, ValueError):
                errors.append('HISTORY_PROVIDER_UNAVAILABLE')
            # Never fetch today's quote/fundamentals for a historical replay.
            if not historical:
                try:
                    quote = self.evidence.current_quote_provider.get_current_quote(ticker)
                except (OSError, RuntimeError, ValueError):
                    errors.append('CURRENT_QUOTE_UNAVAILABLE')
                try:
                    fundamentals = tuple(self.evidence.fundamentals_provider.get_financial_data(ticker))
                except (OSError, RuntimeError, ValueError):
                    errors.append('FUNDAMENTALS_UNAVAILABLE')
            return ticker, (records, quote, fundamentals, errors)

        # Portfolio-wide reviews commonly exceed the former 20-asset screen
        # limit. Bound parallelism per request while preserving each asset's
        # independent source failures and stable display order.
        acquired = {}
        with ThreadPoolExecutor(max_workers=min(MAX_CONCURRENT_ASSETS, len(universe))) as pool:
            futures = [pool.submit(acquire, ticker) for ticker in universe]
            for future in as_completed(futures):
                ticker, evidence = future.result()
                acquired[ticker] = evidence
        dividend_evidence={}
        if not historical:
            from b3_agent.stored_dividends import StoredDividendService
            dividend_service=self.dividend_service or StoredDividendService()
            dividend_evidence={ticker:dividend_service.build(ticker,datetime.now(timezone.utc)) for ticker in universe}
        # Current ingestion can finish after request arrival. Freeze once, after
        # acquisition, then apply the same PIT cutoff to every asset and source.
        cutoff = as_of or datetime.now(timezone.utc)
        metric, direction, window = OBJECTIVES[objective]
        rows, packs, windows = [], {}, {}
        for ticker in universe:
            records, quote, fundamentals, errors = acquired[ticker]
            reasons = list(errors)
            eligible = []
            excluded_pit = 0
            for record in records:
                if not _admissible(record, ticker, cutoff) or record.observation_timestamp.date() < requested_at.date()-timedelta(days=120):
                    excluded_pit += 1
                    continue
                price = record.adjusted_close if record.adjusted_close is not None else record.close
                if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in (price, record.close, record.volume)) or price <= 0 or record.close <= 0 or record.volume < 0:
                    reasons.append('INVALID_HISTORY_VALUE')
                    continue
                eligible.append(record)
            eligible.sort(key=lambda r: r.observation_timestamp)
            if len({r.observation_timestamp.date() for r in eligible}) != len(eligible):
                reasons.append('DUPLICATE_HISTORY_OBSERVATIONS')
                eligible = []
            quant = asdict(compute_quant_features(eligible, as_of=cutoff)) if eligible else {}
            quote = quote if quote is not None and _admissible(quote, ticker, cutoff) and isinstance(quote.close, (int, float)) and not isinstance(quote.close, bool) and math.isfinite(quote.close) and quote.close > 0 else None
            funds = [r for r in fundamentals if _admissible(r, ticker, cutoff) and isinstance(r.value, (int, float)) and not isinstance(r.value, bool) and math.isfinite(r.value)]
            positions = [] if portfolio is None or portfolio.as_of > cutoff.date() else [
                p for p in portfolio.positions if canonical_position_ticker(p) == ticker
            ]
            portfolio_known = portfolio is not None and portfolio.as_of <= cutoff.date()
            stock_positions = [p for p in positions if p.instrument_type.upper() == 'STOCK']
            option_positions = [p for p in positions if p.instrument_type.upper() == 'OPTION']
            positive_stock_shares = sum(max(0.0, p.quantity) for p in stock_positions)
            short_calls = [p for p in option_positions if (p.option_type or '').upper() == 'CALL' and p.quantity < 0]
            short_puts = [p for p in option_positions if (p.option_type or '').upper() == 'PUT' and p.quantity < 0]
            call_units_valid = all(math.isfinite(p.contract_multiplier) and p.contract_multiplier > 0 for p in short_calls)
            put_terms_valid = all(p.strike is not None and math.isfinite(p.strike) and p.strike > 0
                and math.isfinite(p.contract_multiplier) and p.contract_multiplier > 0 for p in short_puts)
            short_call_units = sum(abs(p.quantity) * p.contract_multiplier for p in short_calls) if call_units_valid else None
            covered_call_units = min(positive_stock_shares, short_call_units) if short_call_units is not None else None
            short_put_obligation = (sum(abs(p.quantity) * p.strike * p.contract_multiplier for p in short_puts)
                if put_terms_valid else None)
            if short_call_units is None:
                call_coverage_status = 'UNKNOWN_CONTRACT_MULTIPLIER'
            elif not short_call_units:
                call_coverage_status = 'NO_SHORT_CALL'
            elif covered_call_units >= short_call_units:
                call_coverage_status = 'COVERED'
            elif covered_call_units > 0:
                call_coverage_status = 'PARTIALLY_COVERED'
            else:
                call_coverage_status = 'UNCOVERED'
            holdings = {
                'held': bool(positions) if portfolio_known else None,
                'stock_quantity': sum(p.quantity for p in stock_positions) if portfolio_known else None,
                'open_option_count': len(option_positions) if portfolio_known else None,
                'open_options': [
                    {'contract_ticker':p.ticker, 'option_type':p.option_type, 'quantity':p.quantity,
                     'strike':p.strike, 'expiration_date':p.expiration_date,
                     'contract_multiplier':p.contract_multiplier, 'market_price':p.market_price,
                     'market_value':p.market_value, 'source_ref':p.source_ref}
                    for p in option_positions
                ] if portfolio_known else None,
                'short_put_assignment_capital_brl': short_put_obligation if portfolio_known else None,
                'short_call_units': short_call_units if portfolio_known else None,
                'covered_call_units': covered_call_units if portfolio_known else None,
                'covered_call_status': call_coverage_status if portfolio_known else 'PORTFOLIO_UNKNOWN',
                'snapshot_as_of': portfolio.as_of if portfolio_known else None,
            }
            sources = tuple(dict.fromkeys([*(r.source for r in eligible), *(r.source for r in funds), *((quote.source,) if quote else ()), *((portfolio.source_refs) if portfolio_known and positions else ())]))
            pack = AssetEvidencePack(ticker=ticker, as_of=cutoff,
                market={'history_count':len(eligible), 'history_start':eligible[0].observation_timestamp if eligible else None, 'history_end':eligible[-1].observation_timestamp if eligible else None, 'history_latest':asdict(eligible[-1]) if eligible else None, 'current_quote':asdict(quote) if quote else None},
                quant=quant, fundamentals={'metric_count':len(funds), 'metrics':{r.metric:asdict(r) for r in funds}},
                portfolio=holdings, source_refs=sources, quality_status='WARNING', limitations=tuple(reasons))
            packs[ticker] = asdict(pack)
            value = quant.get(metric) if metric else None
            if metric and (len(eligible) < window or not isinstance(value, (int, float)) or not math.isfinite(value)):
                reasons.append('INSUFFICIENT_OBJECTIVE_SAMPLE')
            if eligible and (cutoff.date()-eligible[-1].observation_timestamp.date()).days > 7:
                reasons.append('STALE_OBJECTIVE_WINDOW')
            if eligible and window and len(eligible) >= window and not any(r in reasons for r in ('INVALID_HISTORY_VALUE', 'DUPLICATE_HISTORY_OBSERVATIONS', 'STALE_OBJECTIVE_WINDOW')):
                windows[ticker] = tuple(r.observation_timestamp.date().isoformat() for r in eligible[-window:])
            row_scope = ('CANDIDATE' if ticker in candidates else
                'PORTFOLIO_STOCK' if ticker in portfolio_stock_tickers else 'OPTION_UNDERLYING_CONTEXT')
            rows.append({'ticker':ticker, 'scope_role':row_scope,
                'discovery_eligible':row_scope != 'OPTION_UNDERLYING_CONTEXT',
                'rank':None, 'objective_value':value,
                'volatility_60d':quant.get('volatility_60d'), 'max_drawdown':quant.get('max_drawdown'), 'liquidity_proxy_20d':quant.get('average_dollar_volume_20d'),
                'current_price':quote.close if quote else None, 'quote_as_of':quote.observation_timestamp if quote else None,
                'portfolio':holdings, 'expected_return':None, 'valuation_status':'UNKNOWN',
                'source_refs':list(sources), 'history_count':len(eligible), 'excluded_pit_or_identity_count':excluded_pit, 'exclusions':reasons,
                'ranking_evidence_ref':f'quant:{ticker}:{POLICY}:{cutoff.isoformat()}'})
        from b3_agent.dividend_evidence import dividend_payload
        from b3_agent.price_target_evidence import StoredPriceTargetService
        from b3_agent.economic_evidence import economic_evidence, rank_target_potential
        target_service=self.target_service or StoredPriceTargetService()
        for row in rows:
            ticker=row['ticker']
            row['dividends']=dividend_payload(ticker,dividend_evidence.get(ticker,{}),cutoff)
            row['institution_targets']=target_service.build(ticker,cutoff) if not historical else {'status':'HISTORICAL_TARGET_READ_NOT_REQUESTED','rows':[]}
            # Economic calculations require a recent qualified current quote.
            spot=row['current_price']
            if row['quote_as_of'] and (cutoff-row['quote_as_of']).total_seconds()>7*86400: spot=None
            projection={'ticker':ticker,'current_price_brl':spot,'dividends':row['dividends'],
                'institution_targets':row['institution_targets'],
                'observed_risk':{k:row.get(k) for k in ('volatility_60d','max_drawdown','liquidity_proxy_20d')}}
            row['economic_evidence']=economic_evidence(projection,budget=budget,entry_cost=costs.get(ticker),portfolio=portfolio)
            row['source_refs'].extend(t['source_url'] for t in row['institution_targets']['rows'])
            row['source_refs'].extend(e['source'] for e in row['dividends']['events'])
            row['source_refs']=list(dict.fromkeys(row['source_refs']))
        economic_ranking=rank_target_potential([r['economic_evidence'] for r in rows],inputs['target_institution'],inputs['target_horizon']) if 'target_institution' in inputs else {'status':'NOT_REQUESTED','rows':[]}
        valid = [r for r in rows if r['discovery_eligible'] and r['ticker'] in windows and r['objective_value'] is not None]
        cohorts = Counter(windows[r['ticker']] for r in valid)
        reference = max(cohorts, key=lambda w:(cohorts[w], w[-1], w)) if cohorts else None
        comparable = [r for r in valid if windows[r['ticker']] == reference]
        for row in valid:
            if row not in comparable:
                row['exclusions'].append('NONCOMPARABLE_OBSERVATION_WINDOW')
        if metric and len(comparable) >= 2:
            comparable.sort(key=lambda r: (r['objective_value'] if direction == 'ascending' else -r['objective_value'], r['ticker']))
            prior, rank = None, None
            for index, row in enumerate(comparable, 1):
                if prior is None or not math.isclose(row['objective_value'], prior, rel_tol=1e-9, abs_tol=1e-12):
                    rank = index
                    prior = row['objective_value']
                row['rank'] = rank
            status = 'RANKED_CONDITIONALLY' if len(comparable) == len(rows) else 'PARTIAL_COMPARABLE_UNIVERSE'
        else:
            status = 'COMPARED_WITHOUT_RANKING' if not metric else 'INSUFFICIENT_COMPARABLE_ASSETS'
        rows.sort(key=lambda r:(r['rank'] is None, r['rank'] or 0, r['ticker']))
        limitations = ['Conditional ordering of observed risk or liquidity, not an expected-return or overall BUY ranking.',
            'Liquidity is an approximation: mean of adjusted close when available (otherwise close) times volume over 20 observations; not actual traded financial turnover.',
            'Targets, valuation, future dividends, costs and trade sizing are not inferred; personal outcomes are not required for this observed-data objective.',
            'Assets with different objective observation windows are not silently compared.']
        if include_portfolio and portfolio is None:
            limitations.append('CURRENT_PORTFOLIO_UNAVAILABLE: candidate analysis completed, but portfolio positions and option exposure could not be joined to this run.')
        unresolved_position_count = unresolved_stock_position_count + unresolved_option_underlying_count
        if include_portfolio and unresolved_position_count:
            limitations.append(
                f'UNRESOLVED_PORTFOLIO_IDENTITY: {unresolved_position_count} position(s) have no valid B3 equity ticker identity and were not joined to an asset; portfolio coverage is partial.'
            )
        if historical:
            limitations.append('Historical replay excludes current quotes, fundamentals and the current portfolio snapshot.')
        portfolio_scope = {
            'status': (
                'UNAVAILABLE' if include_portfolio and portfolio is None else
                'NOT_REQUESTED' if not include_portfolio else
                'PARTIAL' if unresolved_position_count else 'INCLUDED'
            ),
            'snapshot_as_of': portfolio.as_of if portfolio is not None and include_portfolio else None,
            'stock_ticker_count': len(portfolio_stock_tickers),
            'option_position_count': sum(p.instrument_type.upper() == 'OPTION' for p in portfolio.positions) if portfolio is not None and include_portfolio else None,
            'unresolved_identity_position_count': unresolved_position_count if portfolio is not None and include_portfolio else None,
            'unresolved_stock_position_count': unresolved_stock_position_count if portfolio is not None and include_portfolio else None,
            'unresolved_option_underlying_count': unresolved_option_underlying_count if portfolio is not None and include_portfolio else None,
        }
        return {'as_of':cutoff, 'opportunity_screen':{'policy_version':POLICY, 'objective':objective, 'metric':metric, 'direction':direction, 'status':status,
            'maximum_history_age_days':7, 'tie_tolerance':{'relative':1e-9,'absolute':1e-12}, 'sample_observations':window, 'reference_window_start':reference[0] if reference else None, 'reference_window_end':reference[-1] if reference else None,
            'candidate_universe':candidates, 'portfolio_stock_universe':portfolio_stock_tickers,
            'portfolio_option_underlying_universe':portfolio_option_underlying_tickers,
            'portfolio_scope':portfolio_scope, 'requested_universe':universe,
            'ranked_count':sum(r['rank'] is not None for r in rows), 'rows':rows, 'limitations':limitations},
            'economic_target_ranking':economic_ranking, 'asset_evidence':packs, 'limitations':limitations, 'source_refs':list(dict.fromkeys(s for r in rows for s in r['source_refs']))}
