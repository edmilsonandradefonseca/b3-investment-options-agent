from datetime import datetime, timezone
from types import SimpleNamespace
import pytest
from b3_agent.funded_switch import build_funded_switch

class Screen:
    def build(self, assets, **kwargs):
        return {'as_of':datetime(2026,10,3,tzinfo=timezone.utc),'source_refs':['fixture'], 'asset_evidence':{ticker:{'portfolio':{'stock_quantity':100 if index==0 else 0},'market':{'current_quote':{'close':10 if index==0 else 30,'observation_timestamp':datetime(2026,10,2,tzinfo=timezone.utc)}}} for index,ticker in enumerate(assets)}}

def build(inputs):
    return build_funded_switch(['ITUB4','BBDC4'],inputs,screen_service=Screen(),portfolio=SimpleNamespace(positions=[]))

def test_sale_finances_integer_purchase_and_conserves_cash():
    result=build({'quantity':100,'fees_brl':5,'taxes_brl':5})
    facts=result['funded_switch']
    assert facts['gross_sale_proceeds_brl']==1000
    assert facts['buy_quantity']==33 and facts['residual_cash_brl']==0
    assert facts['purchase_notional_brl']+facts['residual_cash_brl']==facts['net_sale_proceeds_brl']==990
    assert facts['remaining_source_stock_quantity']==0
    assert result['strategy_comparison']['expected_return_delta'] is None
    assert facts['execution_authorized'] is False


def test_unknown_costs_do_not_become_zero_or_size_a_purchase():
    facts=build({'quantity':10})['funded_switch']
    assert facts['status']=='COSTS_UNKNOWN'
    assert facts['net_sale_proceeds_brl'] is facts['buy_quantity'] is facts['residual_cash_brl'] is None


def test_zero_cost_scenario_preserves_residual():
    facts=build({'quantity':10,'fees_brl':0,'taxes_brl':0})['funded_switch']
    assert facts['buy_quantity']==3 and facts['residual_cash_brl']==10

@pytest.mark.parametrize('inputs',[{'quantity':101},{'quantity':True},{'quantity':1,'fees_brl':'NaN'},{'quantity':1,'fees_brl':11,'taxes_brl':0}])
def test_invalid_or_unfunded_request_rejects(inputs):
    with pytest.raises(ValueError): build(inputs)
