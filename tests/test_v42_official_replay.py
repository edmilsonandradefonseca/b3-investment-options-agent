from datetime import datetime, timedelta, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from b3_agent.knowledge.evidence import Evidence, EvidenceKind, EvidenceMetadata


script_path = Path(__file__).resolve().parents[1] / "scripts" / "replay_v42_official_fact.py"
spec = spec_from_file_location("replay_v42_official_fact", script_path)
replay = module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(replay)


def _evidence(record_id: str, *, materiality: str, reason: str, when: datetime) -> Evidence:
    return Evidence(
        evidence_id=f"ev:{record_id}",
        kind=EvidenceKind.DOCUMENT,
        title="Fato Relevante" if materiality == "MATERIAL" else "Comunicado",
        content="Official CVM metadata",
        source_url=f"https://www.rad.cvm.gov.br/doc/{record_id}",
        metadata=EvidenceMetadata(
            document_id=record_id,
            source="CVM_OPEN_DATA_IPE",
            published_at=when,
            retrieved_at=when + timedelta(days=1),
            ticker_refs=("PETR4",),
            issuer_ref="cvm:9512",
            cvm_code="9512",
            provider_record_id=f"CVM_OPEN_DATA_IPE|{record_id}|1",
            materiality=materiality,
            materiality_reason=reason,
            materiality_policy_version="v4.2-official-1",
            pit_status="HISTORICAL_RECONSTRUCTION",
            extra={"protocol": record_id},
        ),
    )


def test_replay_selects_latest_real_fato_relevante_and_can_pin_protocol():
    base = datetime(2026, 9, 1, tzinfo=timezone.utc)
    candidate = _evidence(
        "100",
        materiality="CANDIDATE",
        reason="OFFICIAL_COMUNICADO_AO_MERCADO",
        when=base,
    )
    older = _evidence(
        "200",
        materiality="MATERIAL",
        reason="OFFICIAL_FATO_RELEVANTE",
        when=base + timedelta(days=1),
    )
    newer = _evidence(
        "300",
        materiality="MATERIAL",
        reason="OFFICIAL_FATO_RELEVANTE",
        when=base + timedelta(days=2),
    )

    selected = replay.select_material_evidence((candidate, older, newer))
    assert selected.metadata.extra["protocol"] == "300"

    pinned = replay.select_material_evidence(
        (candidate, older, newer),
        protocol="200",
    )
    assert pinned.metadata.extra["protocol"] == "200"
