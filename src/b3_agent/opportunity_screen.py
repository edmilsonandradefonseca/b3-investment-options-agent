"""Objective-specific stock screening; observed risk/liquidity are not valuation."""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import math

from b3_agent.config import settings
from b3_agent.portfolio.snapshot import load_active_snapshots
from b3_agent.quant_engine import compute_quant_features
from b3_agent.schemas.position import PortfolioContext
from b3_agent.strategy_live import AssetEvidencePack, StrategyEvidenceService, _validated_equity_ticker

POLICY = 'B3_OBSERVED_STOCK_SCREEN_V1'
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
    def __init__(self, evidence_service=None):
        self.evidence = evidence_service or StrategyEvidenceService()

    def build(self, tickers, *, objective='COMPARE_ONLY', include_portfolio=False,
              as_of=None, portfolio=None):
        if objective not in OBJECTIVES:
            raise ValueError('Unsupported opportunity objective')
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
        universe = list(dict.fromkeys(_validated_equity_ticker(t) for t in tickers))
        if include_portfolio:
            if portfolio is None:
                raise ValueError('An admissible current portfolio is required to include its stocks')
            universe.extend(_validated_equity_ticker(p.ticker) for p in portfolio.positions if p.instrument_type.upper() == 'STOCK')
            universe = list(dict.fromkeys(universe))
        if not 1 <= len(universe) <= 20:
            raise ValueError('Select 1 to 20 assets; portfolio union is not silently truncated')
        requested_at = as_of or datetime.now(timezone.utc)
        acquired = {}
        for ticker in universe:
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
            acquired[ticker] = (records, quote, fundamentals, errors)
        # Current ingestion can finish after request arrival. Freeze once, after
        # acquisition, then apply the same PIT cutoff to every asset and source.
        cutoff = as_of or datetime.now(timezone.utc)
        metric, direction, window = OBJECTIVES[objective]
        rows, packs, windows = [], {}, {}
        for ticker, (records, quote, fundamentals, errors) in acquired.items():
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
            positions = [] if portfolio is None or portfolio.as_of > cutoff.date() else [p for p in portfolio.positions if (p.underlying_ticker if p.instrument_type.upper() == 'OPTION' and p.underlying_ticker else p.ticker).upper() == ticker]
            portfolio_known = portfolio is not None and portfolio.as_of <= cutoff.date()
            holdings = {
                'held': bool(positions) if portfolio_known else None,
                'stock_quantity': sum(p.quantity for p in positions if p.instrument_type.upper() == 'STOCK') if portfolio_known else None,
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
            rows.append({'ticker':ticker, 'rank':None, 'objective_value':value,
                'volatility_60d':quant.get('volatility_60d'), 'liquidity_proxy_20d':quant.get('average_dollar_volume_20d'),
                'current_price':quote.close if quote else None, 'quote_as_of':quote.observation_timestamp if quote else None,
                'portfolio':holdings, 'expected_return':None, 'valuation_status':'UNKNOWN',
                'source_refs':list(sources), 'history_count':len(eligible), 'excluded_pit_or_identity_count':excluded_pit, 'exclusions':reasons,
                'ranking_evidence_ref':f'quant:{ticker}:{POLICY}:{cutoff.isoformat()}'})
        valid = [r for r in rows if r['ticker'] in windows and r['objective_value'] is not None]
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
        if historical:
            limitations.append('Historical replay excludes current quotes, fundamentals and the current portfolio snapshot.')
        return {'as_of':cutoff, 'opportunity_screen':{'policy_version':POLICY, 'objective':objective, 'metric':metric, 'direction':direction, 'status':status,
            'maximum_history_age_days':7, 'tie_tolerance':{'relative':1e-9,'absolute':1e-12}, 'sample_observations':window, 'reference_window_start':reference[0] if reference else None, 'reference_window_end':reference[-1] if reference else None,
            'requested_universe':universe, 'ranked_count':sum(r['rank'] is not None for r in rows), 'rows':rows, 'limitations':limitations},
            'asset_evidence':packs, 'limitations':limitations, 'source_refs':list(dict.fromkeys(s for r in rows for s in r['source_refs']))}
