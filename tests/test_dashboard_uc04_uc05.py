from datetime import date, datetime, timezone
import openpyxl
import pytest
from b3_agent.dashboard_e2e import DashboardDecisionInputs, DashboardE2EService
from b3_agent.schemas.feature_snapshot import FeatureDomain, FeatureSnapshot, FeatureValue
from b3_agent.schemas.scenario import ScenarioDefinition
from b3_agent.schemas.strategy_comparison import StrategyAlternative

def _btg(path):
    wb=openpyxl.Workbook(); capa=wb.active; capa.title="Capa"; capa["C1"]="Período de 27/09/26 a 27/09/26"
    ws=wb.create_sheet("Renda Variavel"); ws.append(["","Posição > Ações"])
    ws.append(["","Código","Ação","Qtde.","Preço Fechamento R$","Preço Médio R$","Saldo Bruto R$"])
    ws.append(["","ITUB4","ITAU",1000,40,35,40000]); ws.append(["","Total em Ações R$","","","","",40000])
    ws.append(["","Posição > Opções"]); ws.append(["","Código","Ativo Ref.","Qtde.","Preço Exercício R$","Data Exercício R$","Tipo","Posição","Prêmio Mercado R$","Valor de Mercado R$"])
    ws.append(["","Total em Opções R$","","","","","","","",0]); wb.save(path)

def test_dashboard_e2e_converges_uc04_uc05(tmp_path):
    path=tmp_path/"btg.xlsx"; _btg(path); as_of=date(2026,9,27)
    left=StrategyAlternative("hold","Hold","HOLD","ITUB4",as_of,capital_required=0,expected_return=.05,payoff_by_scenario={"bear":-1000})
    right=StrategyAlternative("add","Add","BUY","ITUB4",as_of,capital_required=10000,expected_return=.12,payoff_by_scenario={"bear":-1800})
    scenario=ScenarioDefinition("bear-10","ITUB4 -10%",as_of,ticker_price_shocks={"ITUB4":-.10})
    observed=datetime(2026,9,27,17,tzinfo=timezone.utc)
    features=FeatureSnapshot("market-1","IBOV",observed,features=(
        FeatureValue("close",150000,FeatureDomain.MARKET,observed), FeatureValue("sma_20",145000,FeatureDomain.MARKET,observed),
        FeatureValue("sma_50",140000,FeatureDomain.MARKET,observed), FeatureValue("volatility_20d",.18,FeatureDomain.RISK,observed),
        FeatureValue("foreign_flow_5d",1.0,FeatureDomain.FLOW,observed)),source_refs=("market-features",))
    result=DashboardE2EService().load(path,decision_inputs=DashboardDecisionInputs(strategy_pairs=((left,right),),scenarios=(scenario,),feature_snapshot=features))
    assert result.strategy_comparisons[0].expected_return_delta == pytest.approx(.07)
    assert result.strategy_comparisons[0].assumptions["ranking"] == "not_applied"
    assert result.stress_results[0].portfolio_pnl == -4000
    labels={item.name.value:item.label for item in result.market_regime.dimensions}
    assert labels["TREND"]=="BULL"; assert labels["VOLATILITY"]=="LOW"; assert labels["FOREIGN_FLOW"]=="POSITIVE"
