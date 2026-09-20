from datetime import date

from b3_agent.options.brokerage_notes import BrokerageNoteParser
from b3_agent.repositories.option_ledger import OptionTransactionLedger


NOTE_TEXT = """
NOTA DE CORRETAGEM
34515456
 Nr. nota
1
 Folha
17/09/2026
 Data pregão
Negócios realizados
Q Negociação C/V Tipo Mercado Prazo Especificação do título Obs. (*) Quantidade Preço / Ajuste Valor Operação / Ajuste D/C
1-BOVESPA C OPCAO DE COMPRA 10/26 ASAIJ970 ON 3000 0,94 2.820,00 D
1-BOVESPA V OPCAO DE COMPRA 11/26 ASAIK102 ON 3000 1,04 3.120,00 C
1-BOVESPA V OPCAO DE COMPRA 11/26 ASAIK102 ON 4000 1,03 4.120,00 C
"""

def test_parse_btg_brokerage_note():
    transactions = BrokerageNoteParser().parse_text(NOTE_TEXT, source_file="nota.pdf")

    assert len(transactions) == 3
    assert transactions[0].option_ticker == "ASAIJ970"
    assert transactions[0].side == "BUY"
    assert transactions[0].quantity == 3000
    assert transactions[0].execution_price == 0.94
    assert transactions[0].total_amount == 2820.0
    assert transactions[0].as_of == date(2026, 9, 17)
    assert transactions[0].note_number == "34515456"

    assert transactions[1].side == "SELL"
    assert transactions[2].side == "SELL"
    assert transactions[1].option_ticker == transactions[2].option_ticker


def test_ledger_is_append_only_and_deduplicates(tmp_path):
    transactions = BrokerageNoteParser().parse_text(
        NOTE_TEXT,
        source_file="nota.pdf",
    )
    ledger = OptionTransactionLedger(tmp_path / "options.sqlite3")

    assert ledger.append(transactions) == 3
    assert ledger.append(transactions) == 0

    rows = ledger.list_by_ticker("ASAIK102")
    assert len(rows) == 2
    assert [row.quantity for row in rows] == [-3000, -4000]


def test_brokerage_upload_endpoint_parses_and_persists_note(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    from b3_agent import server

    transactions = BrokerageNoteParser().parse_text(NOTE_TEXT, source_file="nota.pdf")
    monkeypatch.setattr(server.settings, "data_dir", tmp_path)
    monkeypatch.setattr(
        server.BrokerageNoteParser,
        "parse",
        lambda self, path: transactions,
    )

    response = TestClient(server.app).post(
        "/imports/brokerage-notes",
        files={"file": ("nota.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "processed"
    assert payload["parsed_count"] == 3
    assert payload["inserted_count"] == 3
    assert payload["note_number"] == "34515456"

    ledger = OptionTransactionLedger(tmp_path / "options.sqlite3")
    assert len(ledger.list_all()) == 3
