from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import os
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


CVM_RAD_ENDPOINT = "https://seguro.bmfbovespa.com.br/rad/download/SolicitaDownload.asp"
CVM_NO_RECORDS_ERROR = "22016"
CVM_BAD_LOGIN_ERROR = "1"


class CvmRadError(RuntimeError):
    """Base error for CVM Download Múltiplo acquisition."""


class CvmRadCredentialsMissing(CvmRadError):
    """Raised when runtime CVM credentials are absent."""


class CvmRadAuthenticationError(CvmRadError):
    """Raised when CVM rejects the configured credentials."""


@dataclass(frozen=True)
class CvmRadDisclosure:
    provider_record_id: str
    document_url: str
    document_type: str | None
    cvm_code: str | None
    reference_date: date | None
    source_status: str | None
    category: str | None
    disclosure_type: str | None
    species: str | None
    retrieved_at: datetime
    raw_attributes: dict[str, str]


@dataclass(frozen=True)
class CvmRadQueryResult:
    requested_date: date
    requested_time: str
    document_type: str
    retrieved_at: datetime
    disclosures: tuple[CvmRadDisclosure, ...]
    source_error_code: str | None = None


class CvmRadDisclosureProvider:
    """Zero-cost official disclosure provider using CVM Download Múltiplo."""

    def __init__(
        self,
        *,
        username: str | None = None,
        password: str | None = None,
        endpoint: str = CVM_RAD_ENDPOINT,
        timeout: float = 30.0,
    ) -> None:
        self.username = username or os.getenv("CVM_DM_USER") or os.getenv("CVM_LOGIN")
        self.password = password or os.getenv("CVM_DM_PASS") or os.getenv("CVM_PASSWORD")
        self.endpoint = endpoint
        self.timeout = timeout

    @property
    def name(self) -> str:
        return "cvm_rad"

    def query_ipe(
        self,
        requested_date: date,
        *,
        requested_time: str = "00:00",
        assunto_ipe: str = "SIM",
    ) -> CvmRadQueryResult:
        return self.query(
            requested_date,
            requested_time=requested_time,
            document_type="IPE",
            assunto_ipe=assunto_ipe,
        )

    def query(
        self,
        requested_date: date,
        *,
        requested_time: str = "00:00",
        document_type: str = "IPE",
        assunto_ipe: str | None = "SIM",
    ) -> CvmRadQueryResult:
        if not self.username or not self.password:
            raise CvmRadCredentialsMissing(
                "CVM Download Multiplo credentials are missing. "
                "Set CVM_DM_USER/CVM_DM_PASS (or CVM_LOGIN/CVM_PASSWORD) in runtime secrets."
            )
        if not _valid_time(requested_time):
            raise ValueError("requested_time must be HH:MM")

        doc_type = document_type.upper().strip()
        if not doc_type:
            raise ValueError("document_type must not be empty")

        form = {
            "txtLogin": self.username,
            "txtSenha": self.password,
            "txtData": requested_date.strftime("%d/%m/%Y"),
            "txtHora": requested_time,
            "txtDocumento": doc_type,
        }
        if assunto_ipe is not None and doc_type == "IPE":
            form["txtAssuntoIPE"] = assunto_ipe.upper()

        body = urllib.parse.urlencode(form).encode("ascii")
        request = urllib.request.Request(
            self.endpoint,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/xml,text/xml,*/*",
                "User-Agent": "b3-investment-options-agent/0.1",
            },
        )

        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            payload = response.read()

        retrieved_at = datetime.now(timezone.utc)
        root = _parse_xml(payload)

        error_code = root.findtext(".//NUMERO_DO_ERRO")
        if error_code is not None:
            error_code = error_code.strip()
            description = (root.findtext(".//DESCRICAO_DO_ERRO") or "unknown CVM error").strip()
            if error_code == CVM_NO_RECORDS_ERROR:
                return CvmRadQueryResult(
                    requested_date=requested_date,
                    requested_time=requested_time,
                    document_type=doc_type,
                    retrieved_at=retrieved_at,
                    disclosures=(),
                    source_error_code=error_code,
                )
            if error_code == CVM_BAD_LOGIN_ERROR:
                raise CvmRadAuthenticationError(
                    "CVM Download Multiplo rejected the configured credentials"
                )
            raise CvmRadError(
                f"CVM Download Multiplo error {error_code}: {description}"
            )

        disclosures: list[CvmRadDisclosure] = []
        for index, link in enumerate(root.findall(".//Link")):
            attrs = {str(key): str(value) for key, value in link.attrib.items()}
            url = _attr(attrs, "url")
            if not url:
                continue
            cvm_code = _attr(attrs, "ccvm", "codcvm", "codigoCVM")
            document = _attr(attrs, "Documento", "documento")
            reference_raw = _attr(attrs, "DataRef", "dataref")
            status = _attr(attrs, "Situacao", "situacao")
            category = _attr(attrs, "Categoria", "categoria")
            disclosure_type = _attr(attrs, "Tipo", "tipo")
            species = _attr(attrs, "Especie", "especie")
            provider_record_id = _provider_record_id(
                requested_date=requested_date,
                cvm_code=cvm_code,
                document=document,
                reference_raw=reference_raw,
                url=url,
                index=index,
            )
            disclosures.append(
                CvmRadDisclosure(
                    provider_record_id=provider_record_id,
                    document_url=url,
                    document_type=document,
                    cvm_code=cvm_code,
                    reference_date=_parse_br_date(reference_raw),
                    source_status=status,
                    category=category,
                    disclosure_type=disclosure_type,
                    species=species,
                    retrieved_at=retrieved_at,
                    raw_attributes=attrs,
                )
            )

        return CvmRadQueryResult(
            requested_date=requested_date,
            requested_time=requested_time,
            document_type=doc_type,
            retrieved_at=retrieved_at,
            disclosures=tuple(disclosures),
        )


def _parse_xml(payload: bytes) -> ET.Element:
    try:
        return ET.fromstring(payload)
    except ET.ParseError as exc:
        raise CvmRadError(f"invalid CVM Download Multiplo XML: {exc}") from exc


def _attr(attrs: dict[str, str], *names: str) -> str | None:
    lowered = {key.lower(): value for key, value in attrs.items()}
    for name in names:
        value = lowered.get(name.lower())
        if value is not None:
            stripped = value.strip()
            return stripped or None
    return None


def _parse_br_date(value: str | None) -> date | None:
    if not value:
        return None
    text = value.strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    return None


def _valid_time(value: str) -> bool:
    try:
        parsed = datetime.strptime(value, "%H:%M")
    except ValueError:
        return False
    return parsed.strftime("%H:%M") == value


def _provider_record_id(
    *,
    requested_date: date,
    cvm_code: str | None,
    document: str | None,
    reference_raw: str | None,
    url: str,
    index: int,
) -> str:
    return "|".join(
        [
            "CVM_RAD",
            requested_date.isoformat(),
            cvm_code or "",
            document or "",
            reference_raw or "",
            url,
            str(index),
        ]
    )
