from pathlib import Path


DASHBOARD = Path("mvp/dashboard/app_v06.py")


def _source() -> str:
    return DASHBOARD.read_text(encoding="utf-8")


def test_dashboard_source_compiles():
    source = _source()
    compile(source, str(DASHBOARD), "exec")


def test_streamlit_uses_dashboard_e2e_service_for_uploaded_btg_snapshot():
    source = _source()
    assert "DashboardE2EService().load(portfolio_path)" in source
    assert "snapshot.portfolio" in source
    assert "snapshot.portfolio_intelligence" in source
    assert "snapshot.opportunities" in source
    assert 'type=["xlsx", "xlsm"]' in source


def test_brokerage_notes_have_separate_pdf_and_zip_uploaders():
    source = _source()
    assert '"PDFs de notas"' in source
    assert 'type=["pdf"]' in source
    assert '"ZIP de notas"' in source
    assert 'type=["zip"]' in source
    assert "accept_multiple_files=True" in source
    assert "accept_multiple_files=False" in source


def test_brokerage_ingestion_is_append_only_and_uses_explicit_source_contract():
    source = _source()
    assert "BrokerageNoteParser().parse(note_path)" in source
    assert "OptionTransactionLedger" in source
    assert "ledger.append(transactions)" in source
    assert "BROKERAGE_SOURCE_CONTRACT" in source
    assert "BTG Portfolio é autoritativo para a posição atual" in source
    assert "histórico append-only" in source


def test_bulk_brokerage_upload_is_bounded_and_reports_progress():
    source = _source()
    assert "MAX_DIRECT_PDFS = 10" in source
    assert "MAX_ARCHIVE_PDFS = 250" in source
    assert "MAX_ARCHIVE_UNCOMPRESSED_BYTES" in source
    assert "zipfile.ZipFile" in source
    assert "st.progress(" in source
    assert "Processando {index}/{total_files}" in source


def test_uploaded_files_are_streamed_to_temp_storage():
    source = _source()
    assert "uploaded_file.read(1024 * 1024)" in source
    assert "uploaded_file.getvalue()" not in source


def test_options_intelligence_surfaces_execution_history():
    source = _source()
    assert '"Preço executado": item.execution_price' in source
    assert '"Lado": item.side' in source
    assert '"Nota": item.note_number' in source
