from __future__ import annotations

from datetime import date, datetime, timezone

from b3_agent.jobs.macro_refresh import MacroRefreshJob
from b3_agent.repositories.macro import MacroDataRepository
from b3_agent.schemas.macro import MacroObservation


class FakeBcb:
    def __init__(self):
        self.calls = 0

    def get_series(self, indicator, *, start, end):
        self.calls += 1
        observed = datetime(2026, 9, 26, tzinfo=timezone.utc)
        available = datetime(2026, 9, 27, 22, 0, tzinfo=timezone.utc)
        values = {"SELIC": 13.65, "CDI": 0.050788, "IPCA": -0.32}
        series = {"SELIC": 1178, "CDI": 12, "IPCA": 433}
        return [
            MacroObservation(
                instrument_id=f"MACRO-{indicator}",
                ticker=indicator,
                observation_timestamp=observed,
                available_timestamp=available,
                source="bcb_sgs",
                ingested_at=available,
                source_record_id=f"sgs:{series[indicator]}:2026-09-26",
                quality_status="WARNING",
                quality_flags=("availability_is_ingestion_time",),
                indicator=indicator,
                value=values[indicator],
                unit="test",
                reference_period="2026-09-26",
            )
        ]


def test_macro_refresh_is_idempotent(tmp_path):
    repo = MacroDataRepository(tmp_path / "macro")
    adapter = FakeBcb()
    job = MacroRefreshJob(
        adapter=adapter,
        repository=repo,
        lookback_days=120,
    )

    first = job.run(as_of=date(2026, 9, 27))
    second = job.run(as_of=date(2026, 9, 27))

    assert first.fetched == 3
    assert first.inserted == 3
    assert first.duplicates == 0
    assert second.fetched == 3
    assert second.inserted == 0
    assert second.duplicates == 3
    assert len(repo.read_all()) == 3
    assert second.latest_values == {
        "SELIC": 13.65,
        "CDI": 0.050788,
        "IPCA": -0.32,
    }


def test_repository_preserves_first_seen_availability(tmp_path):
    repo = MacroDataRepository(tmp_path / "macro")
    early = datetime(2026, 9, 27, 20, 0, tzinfo=timezone.utc)
    late = datetime(2026, 9, 28, 20, 0, tzinfo=timezone.utc)

    def record(available):
        return MacroObservation(
            instrument_id="MACRO-SELIC",
            ticker="SELIC",
            observation_timestamp=datetime(2026, 9, 26, tzinfo=timezone.utc),
            available_timestamp=available,
            source="bcb_sgs",
            ingested_at=available,
            source_record_id="sgs:1178:2026-09-26",
            indicator="SELIC",
            value=13.65,
            unit="percent_per_year",
            reference_period="2026-09-26",
        )

    repo.upsert([record(early)])
    inserted, duplicates = repo.upsert([record(late)])

    assert inserted == 0
    assert duplicates == 1
    stored = repo.read_all()
    assert len(stored) == 1
    assert stored[0].available_timestamp == early
