from pathlib import Path


def test_streamlit_uses_dashboard_e2e_service_for_uploaded_btg_snapshot():
    source = Path("mvp/dashboard/app_v06.py").read_text(encoding="utf-8")
    assert "DashboardE2EService().load(portfolio_path)" in source
    assert "snapshot.portfolio" in source
    assert "snapshot.portfolio_intelligence" in source
    assert "snapshot.opportunities" in source
    assert 'type=["xlsx", "xlsm"]' in source


def test_brokerage_notes_are_a_separate_append_only_upload_flow():
    source = Path("mvp/dashboard/app_v06.py").read_text(encoding="utf-8")
    assert '"Notas de corretagem"' in source
    assert 'type=["pdf", "zip"]' in source
    assert "accept_multiple_files=True" in source
    assert "BrokerageNoteParser().parse(note_path)" in source
    assert "OptionTransactionLedger" in source
    assert "inserted += ledger.append(transactions)" in source
    assert "não substituem a posição atual do BTG" in source


def test_bulk_brokerage_upload_is_bounded_and_reports_progress():
    source = Path("mvp/dashboard/app_v06.py").read_text(encoding="utf-8")
    assert "MAX_DIRECT_PDFS = 10" in source
    assert "MAX_ARCHIVE_PDFS = 250" in source
    assert "MAX_ARCHIVE_UNCOMPRESSED_BYTES" in source
    assert "zipfile.ZipFile" in source
    assert "st.progress(" in source
    assert "Processando {index}/{total_files}" in source


def test_options_intelligence_surfaces_execution_history():
    source = Path("mvp/dashboard/app_v06.py").read_text(encoding="utf-8")
    assert '"Preço executado": item.execution_price' in source
    assert '"Lado": item.side' in source
    assert '"Nota": item.note_number' in source
    assert "BTG Portfolio é autoritativo para a posição atual" in source


def test_dashboard_source_compiles():
    source = Path("mvp/dashboard/app_v06.py").read_text(encoding="utf-8")
    compile(source, "mvp/dashboard/app_v06.py", "exec")
