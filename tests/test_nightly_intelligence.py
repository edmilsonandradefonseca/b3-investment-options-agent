from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from b3_agent.jobs.nightly_intelligence import NightlyIntelligenceJob


class FakeNews:
    def __init__(self, *, material: bool):
        self.material = material

    def search(self, ticker, *, query=None, limit=8):
        now = datetime.now(timezone.utc)
        if self.material:
            headline = "Empresa anuncia resultado e dividendos"
            summary = "Lucro trimestral e dividendos foram anunciados."
            url = "https://example.com/news"
        else:
            headline = "PETR4 Cotação e indicadores"
            summary = "Página de consulta da ação."
            url = "https://statusinvest.com.br/acoes/petr4"
        return (SimpleNamespace(
            ticker=ticker,
            available_timestamp=now,
            observation_timestamp=now,
            published_date=now.date(),
            source_record_id="x",
            source="test",
            headline=headline,
            source_name="test",
            url=url,
            event_type="NEWS",
            summary=summary,
            relevance=None,
        ),)


class FakeLLM:
    def __init__(self):
        self.calls = 0

    def ask(self, prompt):
        self.calls += 1
        return SimpleNamespace(
            model="deepseek-r1:8b",
            content="Summary: test",
            thinking="",
            total_duration_ns=1,
            eval_count=1,
            eval_duration_ns=1,
        )


def test_nightly_job_persists_manifest_for_material_event(tmp_path):
    job = NightlyIntelligenceJob(output_dir=tmp_path)
    job.news = FakeNews(material=True)
    job.llm = FakeLLM()
    result = job.run(tickers=["PETR4"])
    assert result["ticker_count"] == 1
    assert result["completed"] == 1
    assert result["skipped"] == 0
    assert job.llm.calls == 1
    assert (tmp_path / "PETR4.json").is_file()
    assert (tmp_path / "latest.json").is_file()


def test_nightly_job_skips_static_non_material_page(tmp_path):
    job = NightlyIntelligenceJob(output_dir=tmp_path)
    job.news = FakeNews(material=False)
    job.llm = FakeLLM()
    result = job.run(tickers=["PETR4"])
    assert result["completed"] == 0
    assert result["skipped"] == 1
    assert job.llm.calls == 0


def test_nightly_job_defers_after_deepseek_budget(tmp_path):
    job = NightlyIntelligenceJob(
        output_dir=tmp_path,
        max_deepseek_calls=1,
    )
    job.news = FakeNews(material=True)
    job.llm = FakeLLM()

    result = job.run(tickers=["PETR4", "VALE3"])

    assert result["completed"] == 1
    assert result["deferred"] == 1
    assert result["deepseek_calls"] == 1
    assert job.llm.calls == 1
    assert result["results"][1]["status"] == "deferred_deepseek_budget"
