from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
import pytest
from b3_agent.strategy_live import LiveStrategyComparisonService, StrategyEvidenceService
from test_strategy_live import FakeMarketProvider, FakeFundamentalsProvider, FakeCurrentQuoteProvider, FakeOptionsProvider

class DifferentExpiryOptions(FakeOptionsProvider):
    def get_snapshot(self,ticker,as_of):
        contracts,quotes=super().get_snapshot(ticker,as_of)
        contracts=[replace(contract,expiration_date=date(2026,12,18)) if contract.option_id=='WEGEV490' else contract for contract in contracts]
        return contracts,quotes


def service(provider=None):
    return LiveStrategyComparisonService(evidence_service=StrategyEvidenceService(market_provider=FakeMarketProvider(),fundamentals_provider=FakeFundamentalsProvider(),current_quote_provider=FakeCurrentQuoteProvider()),options_provider=provider or DifferentExpiryOptions())


def compare(provider=None,**kwargs):
    return service(provider).compare(assets=('WEGE3','WEGE3'),strategies=('Vender PUT','Vender PUT'),option_ids=('WEGEV500','WEGEV490'),**kwargs)


def test_different_expiries_keep_own_horizon_and_distinguish_risk_models():
    result=compare()
    pair=result['put_pair_comparison']
    assert pair['different_expiries'] and pair['ranking']=='NOT_REQUESTED'
    rows=pair['rows']
    assert rows[1]['days_to_expiration']>rows[0]['days_to_expiration']
    assert all(row['touch_probability']>=row['expiry_itm_probability'] for row in rows)
    assert all(row['net_expected_return'] is None and row['rank'] is None for row in rows)
    assert rows[0]['early_assignment_status']=='UNKNOWN'
    assert rows[1]['exercise_style']=='EUROPEAN'


def test_only_explicit_objective_orders_and_normalizes_premium():
    pair=compare(put_objective='HIGHEST_GROSS_PREMIUM_PER_CAPITAL_30D')['put_pair_comparison']
    assert pair['ranking']=='CONDITIONAL_OBJECTIVE_ONLY'
    assert pair['rows'][0]['rank']==1
    for row in pair['rows']:
        assert row['gross_premium_per_capital_30d_pct']==pytest.approx(row['gross_premium_per_capital_pct']*30/row['days_to_expiration'])


def test_missing_iv_does_not_become_zero_risk_or_win():
    class NoIV(DifferentExpiryOptions):
        def get_snapshot(self,ticker,as_of):
            contracts,quotes=super().get_snapshot(ticker,as_of)
            return contracts,[replace(quote,implied_volatility=None) for quote in quotes]
    pair=compare(NoIV(),put_objective='LOWEST_MODEL_EXPIRY_ITM')['put_pair_comparison']
    assert pair['ranking']=='UNKNOWN_OBJECTIVE_INPUTS'
    assert all(row['rank'] is None and row['expiry_itm_probability'] is None for row in pair['rows'])


def test_future_or_ambiguous_option_quote_is_rejected():
    class Future(DifferentExpiryOptions):
        def get_snapshot(self,ticker,as_of):
            contracts,quotes=super().get_snapshot(ticker,as_of)
            return contracts,[replace(quote,available_timestamp=datetime.now(timezone.utc)+timedelta(days=1)) for quote in quotes]
    with pytest.raises(ValueError,match='PIT'): compare(Future())
    class Duplicate(DifferentExpiryOptions):
        def get_snapshot(self,ticker,as_of):
            contracts,quotes=super().get_snapshot(ticker,as_of)
            return contracts,quotes+[quotes[0]]
    with pytest.raises(ValueError,match='exactly one'): compare(Duplicate())


def test_common_terminal_horizon_cannot_rank_different_expiries():
    result=compare(scenario_horizon='2026-11-20',scenario_shocks_pct=[-10,0,10],scenario_objective='MAXIMIZE_WORST_CASE_RETURN_ON_CAPITAL')
    assert result['scenario_analysis']['status']=='PARTIAL'
    assert result['scenario_analysis']['objective_policy']['ranked_alternative_id'] is None
