from datetime import date, datetime

import openpyxl

from b3_agent.dashboard_e2e import DashboardE2EService, DashboardOpportunityInputs
from b3_agent.opportunity_pipeline import StockOpportunityInput
from b3_agent.schemas.market import StockMarketData
from b3_agent.schemas.valuation import ValuationRange


def _btg(path):
    wb = openpyxl.Workbook()
    capa = wb.active
    capa.title = "Capa"
    capa["C1"] = "Período de 27/09/26 a 27/09/26"
    ws = wb.create_sheet("Renda Variavel")
    ws.append(["", "Posição > Ações"])
    ws.append(["", "Código", "Ação", "Qtde.", "Preço Fechamento R$", "Preço Médio R$", "Saldo Bruto R$"])
    ws.append(["", "ITUB4", "ITAU", 1000, 15.5, 16.0, 15500])
    ws.append(["", "Total em Ações R$", "", "", "", "", 15500])
    ws.append(["", "Posição > Opções"])
    ws.append(["", "Código", "Ativo Ref.", "Qtde.", "Preço Exercício R$", "Data Exercício R$", "Tipo", "Posição", "Prêmio Mercado R$", "Valor de Mercado R$"])
    ws.append(["", "Total em Opções R$", "", "", "", "", "", "", "", 0])
    wb.save(path)


def test_dashboard_e2e_accepts_explicit_validated_opportunity_inputs(tmp_path):
    path = tmp_path / "btg.xlsx"
    _btg(path)
    observed = datetime(2026, 9, 27, 17)
    market = StockMarketData(
        instrument_id="ITUB4", ticker="ITUB4",
        observation_timestamp=observed, available_timestamp=observed,
        source="BRAPI", ingested_at=observed,
        open=15.5, high=15.5, low=15.5, close=15.5, volume=1000000,
    )
    valuation = ValuationRange(
        instrument_id="ITUB4", ticker="ITUB4", as_of=date(2026, 9, 27),
        method="PB_ROE", bear_value=15, base_value=20, bull_value=25,
        accumulation_price=16, reduce_price=20, sell_price=25,
        source_refs=("valuation-engine",),
    )
    snapshot = DashboardE2EService().load(
        path,
        opportunity_inputs=DashboardOpportunityInputs(
            stock_inputs=(StockOpportunityInput(
                records=(market,), valuation=valuation, source_refs=("BRAPI",)
            ),),
            source_refs=("validated-opportunity-inputs",),
        ),
    )
    assert len(snapshot.opportunities.ranked_opportunities) == 1
    item = snapshot.opportunities.ranked_opportunities[0]
    assert item.opportunity_id == "ITUB4:ACCUMULATE:PB_ROE"
    assert item.eligible is True
    assert "BRAPI" in item.source_refs
    assert "BTG:Renda Variavel" in snapshot.opportunities.source_refs
