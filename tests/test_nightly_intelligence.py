from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from b3_agent.jobs.nightly_intelligence import NightlyIntelligenceJob


class FakeNews:
    def search(self, ticker, limit=8):
        now = datetime.now(timezone.utc)
        return (SimpleNamespace(
            ticker=ticker,
            available_timestamp=now,
            observation_timestamp=now,
            published_date=None,
            source_record_id="x",
            source="test",
            headline="Company announces update",
            source_name="test",
            url="https://example.com/x",
            event_type="NEWS",
            summary="Operational update",
            relevance=None,
        ),)


class FakeLLM:
    def ask(self, prompt):
        return SimpleNamespace(
            model="deepseek-r1:8b",
            content="Summary: test",
            thinking="",
            total_duration_ns=1,
            eval_count=1,
            eval_duration_ns=1,
        )


def test_nightly_job_persists_manifest(tmp_path):
    job = NightlyIntelligenceJob(output_dir=tmp_path)
    job.news = FakeNews()
    job.llm = FakeLLM()
    result = job.run(tickers=["PETR4"])
    assert result["ticker_count"] == 1
    assert result["completed"] == 1
    assert (tmp_path / "PETR4.json").is_file()
    assert (tmp_path / "latest.json").is_file()
