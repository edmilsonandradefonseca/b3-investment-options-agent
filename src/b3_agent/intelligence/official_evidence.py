from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime, time
import hashlib
from typing import Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from b3_agent.config import settings
from b3_agent.intelligence.issuer_registry import IssuerRegistry
from b3_agent.intelligence.materiality import classify_official_disclosure
from b3_agent.knowledge.evidence import Evidence, EvidenceKind, EvidenceMetadata
from b3_agent.providers.cvm_open_data import CvmOpenDataIpeRecord
from b3_agent.providers.cvm_rad import CvmRadDisclosure


class OfficialEvidenceBuilder:
    """Normalize official CVM observations into the canonical V4 Evidence model."""

    def __init__(
        self,
        *,
        registry: IssuerRegistry | None = None,
        timezone_name: str | None = None,
    ) -> None:
        self.registry = registry
        self.timezone = ZoneInfo(timezone_name or settings.timezone)
        self._issuer_cache: dict[tuple[str | None, str | None], Any] = {}
        self._securities_cache: dict[str, tuple[Any, ...]] = {}

    def from_open_data_ipe(self, record: CvmOpenDataIpeRecord) -> Evidence:
        decision = classify_official_disclosure(
            category=record.category,
            disclosure_type=record.disclosure_type,
            species=record.species,
        )
        issuer_ref, tickers = self._resolve_identity(
            cvm_code=record.cvm_code,
            cnpj=record.cnpj,
            as_of=record.reference_date,
        )
        reference_at = self._reference_at(record.reference_date)
        title = _first_text(
            record.subject,
            record.category,
            record.disclosure_type,
            record.species,
            "CVM IPE disclosure",
        )
        content = _official_content(
            company_name=record.company_name,
            category=record.category,
            disclosure_type=record.disclosure_type,
            species=record.species,
            subject=record.subject,
            reference_date=record.reference_date,
            protocol=record.protocol,
            version=record.version,
        )
        document_id = record.protocol or record.provider_record_id
        evidence_id = _evidence_id("CVM_OPEN_DATA_IPE", record.provider_record_id)

        return Evidence(
            evidence_id=evidence_id,
            kind=EvidenceKind.DOCUMENT,
            title=title,
            content=content,
            source_url=_absolute_http_url(record.document_url),
            content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
            metadata=EvidenceMetadata(
                document_id=document_id,
                source="CVM_OPEN_DATA_IPE",
                published_at=record.delivered_at,
                retrieved_at=record.retrieved_at,
                ticker_refs=tickers,
                issuer_ref=issuer_ref,
                cvm_code=record.cvm_code,
                provider_record_id=record.provider_record_id,
                source_class="OFFICIAL_REGULATORY",
                authority_tier=0,
                discovery_channel="CVM_OPEN_DATA",
                transport_reliability="STRUCTURED_PUBLIC",
                reference_at=reference_at,
                first_seen_at=record.retrieved_at,
                observed_at=record.retrieved_at,
                source_status="ARCHIVED",
                acquisition_status="SUCCESS",
                pit_status="HISTORICAL_RECONSTRUCTION",
                materiality=decision.materiality.value,
                materiality_reason=decision.reason,
                materiality_policy_version=decision.policy_version,
                topic="corporate_disclosure",
                source_quality="official",
                confidence=1.0,
                valid_from=record.delivered_at,
                extra={
                    "provider": "cvm_open_data",
                    "cnpj": record.cnpj,
                    "company_name": record.company_name,
                    "category": record.category,
                    "disclosure_type": record.disclosure_type,
                    "species": record.species,
                    "subject": record.subject,
                    "presentation_type": record.presentation_type,
                    "protocol": record.protocol,
                    "version": record.version,
                    "content_status": "METADATA_ONLY",
                    "published_at_semantics": "CVM_DATA_ENTREGA",
                    "published_at_precision": _delivery_precision(record.raw_row),
                    "raw_row": record.raw_row,
                },
            ),
        )

    def from_rad(self, record: CvmRadDisclosure) -> Evidence:
        decision = classify_official_disclosure(
            category=record.category,
            disclosure_type=record.disclosure_type,
            species=record.species,
        )
        issuer_ref, tickers = self._resolve_identity(
            cvm_code=record.cvm_code,
            cnpj=None,
            as_of=record.reference_date,
        )
        reference_at = self._reference_at(record.reference_date)
        title = _first_text(
            record.category,
            record.disclosure_type,
            record.species,
            record.document_type,
            "CVM RAD disclosure",
        )
        content = _official_content(
            company_name=None,
            category=record.category,
            disclosure_type=record.disclosure_type,
            species=record.species,
            subject=None,
            reference_date=record.reference_date,
            protocol=None,
            version=None,
        )
        evidence_id = _evidence_id("CVM_RAD", record.provider_record_id)

        return Evidence(
            evidence_id=evidence_id,
            kind=EvidenceKind.DOCUMENT,
            title=title,
            content=content,
            source_url=_absolute_http_url(record.document_url),
            content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
            metadata=EvidenceMetadata(
                document_id=record.provider_record_id,
                source="CVM_RAD",
                published_at=None,
                retrieved_at=record.retrieved_at,
                ticker_refs=tickers,
                issuer_ref=issuer_ref,
                cvm_code=record.cvm_code,
                provider_record_id=record.provider_record_id,
                source_class="OFFICIAL_REGULATORY",
                authority_tier=0,
                discovery_channel="CVM_RAD",
                transport_reliability="DOCUMENTED_OFFICIAL",
                reference_at=reference_at,
                first_seen_at=record.retrieved_at,
                observed_at=record.retrieved_at,
                source_status=record.source_status,
                acquisition_status="SUCCESS",
                pit_status="OBSERVED_LIVE",
                materiality=decision.materiality.value,
                materiality_reason=decision.reason,
                materiality_policy_version=decision.policy_version,
                topic="corporate_disclosure",
                source_quality="official",
                confidence=1.0,
                valid_from=record.retrieved_at,
                extra={
                    "provider": "cvm_rad",
                    "document_type": record.document_type,
                    "category": record.category,
                    "disclosure_type": record.disclosure_type,
                    "species": record.species,
                    "content_status": "METADATA_ONLY",
                    "raw_attributes": record.raw_attributes,
                },
            ),
        )

    def _resolve_identity(
        self,
        *,
        cvm_code: str | None,
        cnpj: str | None,
        as_of: date | None,
    ) -> tuple[str | None, tuple[str, ...]]:
        if self.registry is None or (not cvm_code and not cnpj):
            return None, ()

        identity_key = (cvm_code, cnpj)
        if identity_key not in self._issuer_cache:
            self._issuer_cache[identity_key] = self.registry.resolve_issuer(
                cvm_code=cvm_code,
                cnpj=cnpj,
            )
        issuer = self._issuer_cache[identity_key]
        if issuer is None:
            return None, ()

        if issuer.issuer_id not in self._securities_cache:
            self._securities_cache[issuer.issuer_id] = self.registry.securities_for_issuer(
                issuer.issuer_id,
                active_only=False,
            )
        securities = self._securities_cache[issuer.issuer_id]
        tickers = tuple(
            security.ticker
            for security in securities
            if security.is_active(as_of=as_of)
        )
        return issuer.issuer_id, tickers

    def _reference_at(self, value: date | None) -> datetime | None:
        if value is None:
            return None
        return datetime.combine(value, time.min, tzinfo=self.timezone)


def evidence_for_reasoning(evidence: Evidence) -> dict[str, Any]:
    """Bounded canonical Evidence projection for LLM reasoning.

    Append-only/audit payloads retain the full metadata dictionary through
    evidence_to_dict(). Local/senior reasoning receives only provenance,
    temporal, identity and materiality fields that can support a claim.
    Provider raw rows/attributes are intentionally excluded.
    """
    metadata = evidence.metadata

    def dt(value: datetime | None) -> str | None:
        return value.isoformat() if value is not None else None

    return {
        "evidence_id": evidence.evidence_id,
        "kind": evidence.kind.value,
        "title": evidence.title,
        "content": evidence.content,
        "source_url": evidence.source_url,
        "content_hash": evidence.content_hash,
        "metadata": {
            "document_id": metadata.document_id,
            "source": metadata.source,
            "published_at": dt(metadata.published_at),
            "retrieved_at": dt(metadata.retrieved_at),
            "reference_at": dt(metadata.reference_at),
            "first_seen_at": dt(metadata.first_seen_at),
            "observed_at": dt(metadata.observed_at),
            "ticker_refs": list(metadata.ticker_refs),
            "issuer_ref": metadata.issuer_ref,
            "cvm_code": metadata.cvm_code,
            "provider_record_id": metadata.provider_record_id,
            "source_class": metadata.source_class,
            "authority_tier": metadata.authority_tier,
            "discovery_channel": metadata.discovery_channel,
            "transport_reliability": metadata.transport_reliability,
            "source_status": metadata.source_status,
            "acquisition_status": metadata.acquisition_status,
            "pit_status": metadata.pit_status,
            "materiality": metadata.materiality,
            "materiality_reason": metadata.materiality_reason,
            "materiality_policy_version": metadata.materiality_policy_version,
            "topic": metadata.topic,
            "source_quality": metadata.source_quality,
            "confidence": metadata.confidence,
        },
    }


def evidence_to_dict(evidence: Evidence) -> dict[str, Any]:
    """JSON-safe representation for append-only job artifacts."""

    metadata = asdict(evidence.metadata)
    for key in (
        "published_at",
        "retrieved_at",
        "reference_at",
        "first_seen_at",
        "observed_at",
        "valid_from",
        "valid_to",
    ):
        value = metadata.get(key)
        if isinstance(value, datetime):
            metadata[key] = value.isoformat()
    for key in ("retention_class", "decay_profile"):
        value = metadata.get(key)
        if hasattr(value, "value"):
            metadata[key] = value.value
    for key in ("ticker_refs", "sector_refs", "event_refs"):
        value = metadata.get(key)
        if isinstance(value, tuple):
            metadata[key] = list(value)

    return {
        "evidence_id": evidence.evidence_id,
        "kind": evidence.kind.value,
        "title": evidence.title,
        "content": evidence.content,
        "source_url": evidence.source_url,
        "content_hash": evidence.content_hash,
        "metadata": metadata,
    }


def _evidence_id(prefix: str, provider_record_id: str) -> str:
    digest = hashlib.sha256(provider_record_id.encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


def _absolute_http_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return value


def _first_text(*values: str | None) -> str:
    for value in values:
        if value and value.strip():
            return value.strip()
    raise ValueError("official evidence title cannot be empty")


def _official_content(
    *,
    company_name: str | None,
    category: str | None,
    disclosure_type: str | None,
    species: str | None,
    subject: str | None,
    reference_date: date | None,
    protocol: str | None,
    version: str | None,
) -> str:
    fields = (
        ("Company", company_name),
        ("Category", category),
        ("Type", disclosure_type),
        ("Species", species),
        ("Subject", subject),
        ("Reference date", reference_date.isoformat() if reference_date else None),
        ("Protocol", protocol),
        ("Version", version),
    )
    lines = [f"{label}: {value}" for label, value in fields if value]
    if not lines:
        return "Official CVM disclosure metadata."
    return "\n".join(lines)


def _delivery_precision(raw_row: dict[str, str]) -> str:
    value = str(raw_row.get("data_entrega") or "").strip()
    if not value:
        return "UNKNOWN"
    if len(value) == 10:
        return "DATE"
    if ":" in value:
        return "SECOND" if value.count(":") >= 2 else "MINUTE"
    return "UNKNOWN"
