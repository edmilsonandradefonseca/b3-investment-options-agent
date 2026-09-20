from __future__ import annotations

from datetime import date
from pathlib import Path

from openpyxl import Workbook


def make_btg_portfolio(path: Path) -> None:
    wb = Workbook()
    capa = wb.active
    capa.title = "Capa"
    capa["A1"] = "Período de 01/09/26 a 19/09/26"
    sheet = wb.create_sheet("Renda Variavel")
    sheet.append(["Posição > Ações"])
    sheet.append(["", "Código", "", "Quantidade", "Preço Atual", "Preço Médio", "Valor Atual"])
    sheet.append(["", "PETR4", "", 100, 38.50, 32.00, 3850.00])
    sheet.append(["", "VALE3", "", 50, 65.00, 60.00, 3250.00])
    sheet.append(["", "Total em Ações"])
    sheet.append([])
    sheet.append(["Posição > Opções"])
    sheet.append(["", "Código", "Ativo", "Quantidade", "Strike", "Vencimento", "Tipo", "", "Preço Atual", "Valor Atual"])
    sheet.append(["", "PETRV300", "PETR4", -1, 30.00, date(2026, 10, 16), "PUT", "", 0.70, -70.00])
    wb.save(path)


def make_options_transactions(path: Path) -> None:
    wb = Workbook()
    sheet = wb.active
    sheet.append(["Ativo", "Corretora", "Qtd.", "Custo Médio", "Custo Total"])
    sheet.append(["PETRV300", "BTG", -100, 1.20, -120.00])
    sheet.append(["PETRV300", "BTG", 100, 0.80, 80.00])
    sheet.append(["VALEL650", "BTG", -50, 0.90, -45.00])
    sheet.append(["VALEL650", "BTG", 50, 0.40, 20.00])
    wb.save(path)


def make_brokerage_note(path: Path) -> None:
    path.write_bytes(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n")


def prepare(base: Path) -> None:
    imports = base / "imports"
    imports.mkdir(parents=True, exist_ok=True)
    make_btg_portfolio(imports / "portfolio.xlsx")
    make_options_transactions(imports / "options_transactions.xlsx")
    make_btg_portfolio(base / "portfolio-upload.xlsx")
    make_options_transactions(base / "options-upload.xlsx")
    make_brokerage_note(base / "nota-corretagem.pdf")
