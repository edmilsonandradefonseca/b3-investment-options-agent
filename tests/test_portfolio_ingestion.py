from datetime import date

import openpyxl

from b3_agent.portfolio.ingestion import BtgRendaVariavelLoader


def _workbook(path):
    wb = openpyxl.Workbook()
    capa = wb.active
    capa.title = "Capa"
    capa["C1"] = "Período de 11/09/26 a 11/09/26"
    ws = wb.create_sheet("Renda Variavel")
    ws.append([])
    ws.append(["", "Renda Variável"])
    ws.append([])
    ws.append(["", "Posição > Ações"])
    ws.append(["", "Código", "Ação", "Qtde.", "Preço Fechamento R$", "Preço Médio R$", "Saldo Bruto R$"])
    ws.append(["", "ABEV3*", "AMBEV", -7000, 15.74, 16.34, -109410])
    ws.append(["", "ITUB4*", "ITAU", 2060, 42.35, "-", 87179.20])
    ws.append(["", "Total em Ações R$", "", "", "", "", 1574158.89])
    ws.append([])
    ws.append(["", "Posição > Opções"])
    ws.append(["", "Código", "Ativo Ref.", "Qtde.", "Preço Exercício R$", "Data Exercício R$", "Tipo", "Posição", "Prêmio Mercado R$", "Valor de Mercado R$"])
    ws.append(["", "ITUBV403*", "ITUB4", -2000, 40.01, date(2026,10,16), "Put", "vendida", 0.64, -1280])
    ws.append(["", "ITUBJ438*", "ITUB4", -2000, 43.51, date(2026,10,16), "Call", "vendida", 1.52, -3040])
    ws.append(["", "Total em Opções R$", "", "", "", "", "", "", "", -4320])
    wb.save(path)


def test_loads_positions_and_preserves_signed_market_values(tmp_path):
    path = tmp_path / "btg.xlsx"
    _workbook(path)
    context = BtgRendaVariavelLoader().load(path)

    assert context.as_of == date(2026, 9, 11)
    assert len(context.positions) == 4
    assert context.positions[0].market_value == -109410
    option = context.positions[2]
    assert option.ticker == "ITUBV403"
    assert option.quantity == -2000
    assert option.underlying_ticker == "ITUB4"
    assert option.option_type == "PUT"
    assert option.strike == 40.01
    assert option.market_value == -1280


def test_auxiliary_sections_are_not_ingested(tmp_path):
    path = tmp_path / "btg.xlsx"
    _workbook(path)
    context = BtgRendaVariavelLoader().load(path)
    assert all(p.ticker not in {"ASAI3", "DIRR3"} for p in context.positions)
