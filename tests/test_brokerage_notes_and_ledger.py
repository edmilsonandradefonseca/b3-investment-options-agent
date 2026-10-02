from datetime import date

import pytest

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


def test_parse_option_purchase_keeps_unit_price_and_total_from_brokerage_note():
    text = """
NOTA DE CORRETAGEM
34515456
17/09/2026
Q Negociação C/V Tipo Mercado Prazo Especificação do título Obs. (*) Quantidade Preço / Ajuste Valor Operação / Ajuste D/C
1-BOVESPA C OPCAO DE COMPRA 10/26 PCARJ40 ON 52000 0,02 1.040,00 D
"""
    transaction = BrokerageNoteParser().parse_text(text)[0]

    assert transaction.option_ticker == "PCARJ40"
    assert transaction.side == "BUY"
    assert transaction.quantity == 52000
    assert transaction.execution_price == 0.02
    assert transaction.total_amount == 1040.0


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


def test_blank_share_class_and_day_trade_preserve_existing_ids(tmp_path):
    parser = BrokerageNoteParser()
    legacy = parser.parse_text(NOTE_TEXT)
    extra = "1-BOVESPA C OPCAO DE VENDA 05/26 ITUBQ406W4 PN D 1000 1,38 1.380,00 D"
    blank_class = "1-BOVESPA V OPCAO DE VENDA 06/26 ABEVR161 100 0,13 13,00 C"
    text = NOTE_TEXT.replace("1-BOVESPA C", extra + "\n1-BOVESPA C", 1)
    rows = parser.parse_text(text + blank_class + "\n")
    assert len(rows) == 5
    assert rows[0].quantity == 1000
    assert rows[0].total_amount == 1380
    assert [row.transaction_id for row in rows[1:4]] == [
        row.transaction_id for row in legacy
    ]
    assert rows[-1].quantity == -100
    assert rows[-1].total_amount == -13
    ledger = OptionTransactionLedger(tmp_path / "options.sqlite3")
    assert ledger.append(legacy) == 3
    assert ledger.append(rows) == 2
    assert ledger.append(parser.parse_text(text + blank_class + "\n", source_file="copy.pdf")) == 0


def test_unsupported_option_row_rejects_entire_note():
    text = NOTE_TEXT + "1-BOVESPA V OPCAO DE VENDA 06/26 ABEVR161 ON UNKNOWN 100 0,13 13,00 C\n"
    with pytest.raises(ValueError, match="avoid partial execution history"):
        BrokerageNoteParser().parse_text(text)


def test_identical_fills_in_same_note_survive_copy_reimport(tmp_path):
    parser = BrokerageNoteParser()
    line = "1-BOVESPA V OPCAO DE COMPRA 11/26 ASAIK102 ON 4000 1,03 4.120,00 C"
    rows = parser.parse_text(NOTE_TEXT + line + "\n")
    ledger = OptionTransactionLedger(tmp_path / "options.sqlite3")
    # A pre-fix ledger already has the first occurrence. Restore the missing
    # distinct fill while retaining the economic fingerprint of existing rows.
    assert ledger.append(rows[:3]) == 3
    assert ledger.append(rows) == 1
    assert ledger.append(parser.parse_text(NOTE_TEXT + line + "\n", source_file="copy.pdf")) == 0
    assert len(ledger.list_all()) == 4


def test_previously_skipped_identical_fill_before_legacy_row_is_recovered(tmp_path):
    parser = BrokerageNoteParser()
    legacy_rows = parser.parse_text(NOTE_TEXT)
    old_line = "1-BOVESPA C OPCAO DE COMPRA 10/26 ASAIJ970 ON 3000 0,94 2.820,00 D"
    new_line = old_line.replace("ON 3000", "ON D 3000")
    text = NOTE_TEXT.replace(old_line, new_line + "\n" + old_line)
    ledger = OptionTransactionLedger(tmp_path / "options.sqlite3")
    assert ledger.append(legacy_rows) == 3
    assert ledger.append(parser.parse_text(text)) == 1
    assert ledger.append(parser.parse_text(text)) == 0
    assert len(ledger.list_all()) == 4


def test_brokerage_upload_endpoint_parses_and_persists_note(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    from b3_agent import server

    transactions = BrokerageNoteParser().parse_text(NOTE_TEXT, source_file="nota.pdf")
    monkeypatch.setattr(
        server,
        "settings",
        type("TestSettings", (), {"data_dir": tmp_path})(),
    )
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



def test_brokerage_batch_endpoint_processes_zip(monkeypatch, tmp_path):
    from io import BytesIO
    import zipfile
    from fastapi.testclient import TestClient
    from b3_agent import server

    monkeypatch.setattr(
        server,
        "settings",
        type("TestSettings", (), {"data_dir": tmp_path})(),
    )

    expected = {
        "status": "processed",
        "files_total": 2,
        "files_processed": 2,
        "files_failed": 0,
        "parsed_count": 4,
        "inserted_count": 4,
        "processed": [],
        "failures": [],
    }

    monkeypatch.setattr(
        server.BrokerageBatchIngestionService,
        "ingest_zip",
        lambda self, path: expected,
    )

    payload = BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr("nota1.pdf", b"%PDF-1.4 fake")
        archive.writestr("nota2.pdf", b"%PDF-1.4 fake")

    response = TestClient(server.app).post(
        "/imports/brokerage-notes/batch",
        files={"file": ("notas.zip", payload.getvalue(), "application/zip")},
    )

    assert response.status_code == 200
    assert response.json() == expected


def test_brokerage_batch_upload_page_is_available():
    from fastapi.testclient import TestClient
    from b3_agent import server

    response = TestClient(server.app).get("/imports/brokerage-notes/upload")

    assert response.status_code == 200
    assert "Importar ZIP de notas de corretagem" in response.text
    assert 'action="/imports/brokerage-notes/batch"' in response.text
