from datetime import date

import openpyxl
import pytest

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


def _income_workbook(path, *, net=17.0, payment_date=date(2026, 9, 11)):
    _workbook(path)
    wb = openpyxl.load_workbook(path)
    ws = wb["Renda Variavel"]
    ws.append(["", "Movimentação > Ações"])
    ws.append(["", "Data", "Transação", "Código", "Qtde.", "Preço R$", "Valor Bruto R$", "Corretagem e Emolumentos R$", "Valor Líquido R$"])
    ws.append(["", payment_date, "JUROS S/CAPITAL", "ITUB4", 100, "-", 20, "-", net])
    ws.append(["", payment_date, "RECEBIMENTO DIVIDENDOS", "ITUB4", 200, "-", 30, "-", 30])
    ws.append(["", payment_date, "RENDIMENTO", "ITUB4", 100, "-", 50, "-", 40])
    ws.append(["", payment_date, "RESTITUIÇÃO DE CAPITAL", "ITUB4", 100, "-", 90, "-", 90])
    ws.append(["", "Posição > Ações | Aluguel"])
    # A row in the next section must never enter stock distributions.
    ws.append(["", payment_date, "RECEBIMENTO DIVIDENDOS", "ITUB4", 100, "-", 900, "-", 900])
    wb.save(path)
    wb.close()


def test_received_income_is_period_scoped_and_keeps_source_amounts(tmp_path):
    path = tmp_path / "btg.xlsx"
    _income_workbook(path)
    income = BtgRendaVariavelLoader().load(path).received_income
    assert income.period_start == income.period_end == date(2026, 9, 11)
    assert len(income.payments) == 2
    assert income.payments[0].gross_amount == 20
    assert income.payments[0].net_amount == 17
    assert income.payments[0].quantity == 100
    summary = income.summaries[0]
    assert (summary.dividends_net, summary.jcp_net, summary.total_net) == (30, 17, 47)
    assert summary.payment_count == 2
    assert income.payments[0].source_ref.endswith(":row:17")


def test_missing_income_stays_unknown_but_explicit_zero_is_preserved(tmp_path):
    path = tmp_path / "btg.xlsx"
    _workbook(path)
    assert BtgRendaVariavelLoader().load(path).received_income is None
    _income_workbook(path, net="-")
    summary = BtgRendaVariavelLoader().load(path).received_income.summaries[0]
    assert summary.jcp_net is None
    assert summary.total_net is None
    assert summary.dividends_net == 30
    _income_workbook(path, net=0)
    summary = BtgRendaVariavelLoader().load(path).received_income.summaries[0]
    assert summary.jcp_net == 0
    assert summary.total_net == 30


def test_received_income_rejects_payment_after_statement_cutoff(tmp_path):
    path = tmp_path / "btg.xlsx"
    _income_workbook(path, payment_date=date(2026, 9, 12))
    with pytest.raises(ValueError, match="identity/date"):
        BtgRendaVariavelLoader().load(path)


def test_reimported_portfolio_exposes_same_income_without_accumulation(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    from b3_agent import server

    path = tmp_path / "statement.xlsx"
    _income_workbook(path)
    monkeypatch.setattr(server, "settings", type("TestSettings", (), {"data_dir": tmp_path / "data"})())
    client = TestClient(server.app)
    for index in range(2):
        response = client.post("/imports/portfolio", files={"file": (f"statement-{index}.xlsx", path.read_bytes(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        assert response.status_code == 200
        income = client.get("/portfolio/current").json()["received_income"]
        assert len(income["payments"]) == 2
        assert income["summaries"][0]["total_net"] == 47
        assert income["period_start"] == "2026-09-11"


def test_duplicate_distribution_rows_are_not_counted_twice(tmp_path):
    path = tmp_path / "btg.xlsx"
    _income_workbook(path)
    wb = openpyxl.load_workbook(path)
    ws = wb["Renda Variavel"]
    ws.insert_rows(19, 3)
    for row, kind, ticker, gross, net in (
        (19, "JUROS S/CAPITAL", "ITUB4", 20, 17),  # duplicate
        (20, "JUROS S/CAPITAL", "BBDC4", 20, 17), # different ticker
        (21, "RECEBIMENTO DIVIDENDOS", "ITUB4", 20, 17), # different type
    ):
        for col, value in enumerate(["", date(2026, 9, 11), kind, ticker, 100, "-", gross, "-", net], 1):
            ws.cell(row, col, value)
    wb.save(path)
    wb.close()
    income = BtgRendaVariavelLoader().load(path).received_income
    assert income.duplicate_rows_omitted == 1
    assert len(income.payments) == 4
    by_ticker = {row.ticker: row for row in income.summaries}
    assert by_ticker["ITUB4"].jcp_net == 17
    assert by_ticker["ITUB4"].dividends_net == 47
    assert by_ticker["BBDC4"].total_net == 17
