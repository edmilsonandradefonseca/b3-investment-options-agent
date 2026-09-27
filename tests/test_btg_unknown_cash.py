from datetime import date
import openpyxl
from b3_agent.portfolio.ingestion import BtgRendaVariavelLoader
from b3_agent.portfolio.capital_risk import CapitalRiskEngine

def test_btg_renda_variavel_does_not_invent_zero_cash(tmp_path):
    path=tmp_path/"btg.xlsx"; wb=openpyxl.Workbook(); capa=wb.active; capa.title="Capa"; capa["A1"]="Período de 01/09/26 a 27/09/26"; ws=wb.create_sheet("Renda Variavel")
    ws.append(["","Posição > Ações"]); ws.append(["","Código","Ação","Qtde.","Preço Fechamento R$","Preço Médio R$","Saldo Bruto R$"]); ws.append(["","ITUB4","ITAU",100,40,35,4000]); ws.append(["","Total em Ações R$","","","","",4000])
    ws.append(["","Posição > Opções"]); ws.append(["","Código","Ativo Ref.","Qtde.","Preço Exercício R$","Data Exercício R$","Tipo","Posição","Prêmio Mercado R$","Valor de Mercado R$"]); ws.append(["","ITUBV403","ITUB4",-100,40,date(2026,10,16),"PUT","",-1,-100]); ws.append(["","Total em Opções R$","","","","","","","","-100"]); wb.save(path)
    portfolio=BtgRendaVariavelLoader().load(path); risk=CapitalRiskEngine().assess(portfolio)
    assert portfolio.cash_is_known is False
    assert risk.assignment_capital == 4000
    assert risk.cash_after_assignment is None
    assert risk.fully_cash_secured is None
