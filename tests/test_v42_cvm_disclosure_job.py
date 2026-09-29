from datetime import date, datetime, timezone
from types import SimpleNamespace

from b3_agent.jobs.cvm_disclosures import CvmDisclosureJob


NOW = datetime(2026, 9, 29, 20, 0, tzinfo=timezone.utc)


class FakeProvider:
    name = "cvm_rad"

    def query_ipe(self, requested_date):
        return SimpleNamespace(
            source_error_code=None,
            disclosures=(
                SimpleNamespace(
                    provider_record_id="CVM_RAD|1",
                    cvm_code="9512",
                    document_type="IPE",
                    category="Fato Relevante",
                    disclosure_type="Fato Relevante",
                    species=None,
                    reference_date=requested_date,
                    source_status="Liberado",
                    document_url="https://example.test/doc",
                    retrieved_at=NOW,
                    raw_attributes={"Categoria": "Fato Relevante"},
                ),
            ),
        )


def test_cvm_disclosure_job_persists_append_only_run_and_latest(tmp_path):
    job = CvmDisclosureJob(provider=FakeProvider(), output_dir=tmp_path)

    result = job.run(requested_date=date(2026, 9, 29))

    assert result["document_count"] == 1
    assert result["material_count"] == 1
    assert result["disclosures"][0]["materiality_reason"] == "OFFICIAL_FATO_RELEVANTE"
    assert (tmp_path / "latest.json").is_file()
    run_files = list((tmp_path / "runs").glob("*.json"))
    assert len(run_files) == 1
