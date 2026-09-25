from datetime import date, datetime

from b3_agent.repositories.source_manifest import (
    SourceManifestRecord,
    SourceManifestRepository,
)


def test_source_manifest_round_trip(tmp_path) -> None:
    repository = SourceManifestRepository(tmp_path / "manifest.sqlite3")
    record = SourceManifestRecord(
        source_fingerprint="abc123",
        source_type="BROKERAGE_NOTE",
        source_id="34515456",
        source_ref="BTG:NotaCorretagem:34515456",
        file_name="note.pdf",
        imported_at=datetime(2026, 9, 19, 12, 0),
        record_count=9,
        coverage_start=date(2026, 9, 17),
        coverage_end=date(2026, 9, 17),
        scope="PERIOD_ONLY",
        completeness="UNKNOWN",
    )

    repository.upsert(record)
    rows = repository.list_all()

    assert rows == (record,)


def test_source_manifest_upsert_is_idempotent(tmp_path) -> None:
    repository = SourceManifestRepository(tmp_path / "manifest.sqlite3")
    record = SourceManifestRecord(
        source_fingerprint="abc123",
        source_type="OPTIONS_XLSX",
        source_id="options.xlsx",
        source_ref="Options Transactions XLSX",
        file_name="options.xlsx",
        imported_at=datetime(2026, 9, 19, 12, 0),
        record_count=28,
    )

    repository.upsert(record)
    repository.upsert(record)

    assert len(repository.list_all()) == 1
