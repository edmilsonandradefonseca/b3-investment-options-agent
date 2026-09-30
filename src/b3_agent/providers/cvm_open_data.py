from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime, timezone
import hashlib
import io
import re
import unicodedata
import urllib.request
import zipfile


CVM_OPEN_DATA_ROOT = "https://dados.cvm.gov.br/dados/CIA_ABERTA"
CVM_IPE_URL_TEMPLATE = (
    CVM_OPEN_DATA_ROOT + "/DOC/IPE/DADOS/ipe_cia_aberta_{year}.zip"
)
CVM_CAD_URL = CVM_OPEN_DATA_ROOT + "/CAD/DADOS/cad_cia_aberta.csv"
CVM_FCA_URL_TEMPLATE = (
    CVM_OPEN_DATA_ROOT + "/DOC/FCA/DADOS/fca_cia_aberta_{year}.zip"
)


class CvmOpenDataError(RuntimeError):
    """Raised when an official CVM Open Data dataset cannot be acquired or parsed."""


@dataclass(frozen=True)
class CvmOpenDataIpeRecord:
    provider_record_id: str
    cnpj: str | None
    cvm_code: str | None
    company_name: str | None
    reference_date: date | None
    category: str | None
    disclosure_type: str | None
    species: str | None
    subject: str | None
    delivered_at: datetime | None
    presentation_type: str | None
    protocol: str | None
    version: str | None
    document_url: str | None
    retrieved_at: datetime
    raw_row: dict[str, str]


@dataclass(frozen=True)
class CvmOpenDataIpeResult:
    year: int
    source_url: str
    retrieved_at: datetime
    records: tuple[CvmOpenDataIpeRecord, ...]


@dataclass(frozen=True)
class CvmOpenDataIssuerRecord:
    cvm_code: str | None
    cnpj: str | None
    legal_name: str
    trading_name: str | None
    registration_status: str | None
    retrieved_at: datetime
    raw_row: dict[str, str]


@dataclass(frozen=True)
class CvmOpenDataIssuerResult:
    source_url: str
    retrieved_at: datetime
    issuers: tuple[CvmOpenDataIssuerRecord, ...]


@dataclass(frozen=True)
class CvmOpenDataSecurityRecord:
    cnpj: str | None
    company_name: str | None
    reference_date: date | None
    ticker: str
    security_type: str | None
    security_description: str | None
    market: str | None
    exchange: str | None
    trading_start: date | None
    trading_end: date | None
    retrieved_at: datetime
    raw_row: dict[str, str]

    def is_active(self, *, as_of: date | None = None) -> bool:
        target = as_of or date.today()
        if self.trading_start is not None and self.trading_start > target:
            return False
        return self.trading_end is None or self.trading_end >= target


@dataclass(frozen=True)
class CvmOpenDataSecurityResult:
    year: int
    source_url: str
    retrieved_at: datetime
    securities: tuple[CvmOpenDataSecurityRecord, ...]


class CvmOpenDataProvider:
    """Zero-cost official CVM Open Data provider for IPE, CAD and FCA datasets.

    IPE is the V4.2 history/backfill/reconciliation lane. CAD supplies issuer
    identity (CVM code/CNPJ/names), while FCA valor_mobiliario supplies the
    official issuer-to-B3 trading-code relationship used by Issuer Registry.
    """

    def __init__(
        self,
        *,
        timeout: float = 45.0,
        user_agent: str = "b3-investment-options-agent/0.1",
        ipe_url_template: str = CVM_IPE_URL_TEMPLATE,
        cad_url: str = CVM_CAD_URL,
        fca_url_template: str = CVM_FCA_URL_TEMPLATE,
    ) -> None:
        self.timeout = timeout
        self.user_agent = user_agent
        self.ipe_url_template = ipe_url_template
        self.cad_url = cad_url
        self.fca_url_template = fca_url_template

    @property
    def name(self) -> str:
        return "cvm_open_data"

    def fetch_ipe_year(
        self,
        year: int,
        *,
        cvm_codes: tuple[str, ...] = (),
        cnpjs: tuple[str, ...] = (),
        categories: tuple[str, ...] = (),
    ) -> CvmOpenDataIpeResult:
        _validate_year(year, minimum=2003)
        url = self.ipe_url_template.format(year=year)
        payload, retrieved_at = self._download(url)
        rows = _read_zip_csv(
            payload,
            preferred_member=f"ipe_cia_aberta_{year}.csv",
        )

        wanted_codes = {_normalize_cvm_code(value) for value in cvm_codes if value}
        wanted_codes.discard(None)
        wanted_cnpjs = {_normalize_cnpj(value) for value in cnpjs if value}
        wanted_cnpjs.discard(None)
        wanted_categories = {_normalize_text(value) for value in categories if value}

        records: list[CvmOpenDataIpeRecord] = []
        for row in rows:
            cvm_code = _normalize_cvm_code(_value(row, "codigo_cvm", "cd_cvm"))
            cnpj = _normalize_cnpj(_value(row, "cnpj_companhia", "cnpj_cia"))
            category = _clean(_value(row, "categoria"))

            if wanted_codes and cvm_code not in wanted_codes:
                continue
            if wanted_cnpjs and cnpj not in wanted_cnpjs:
                continue
            if wanted_categories and _normalize_text(category or "") not in wanted_categories:
                continue

            protocol = _clean(_value(row, "protocolo_entrega", "protocolo"))
            version = _clean(_value(row, "versao", "versão"))
            reference_date = _parse_date(
                _value(row, "data_referencia", "dt_refer", "data_ref")
            )
            delivered_at = _parse_datetime(
                _value(row, "data_entrega", "dt_entrega")
            )
            document_url = _clean(
                _value(row, "link_download", "link_doc", "url", "link")
            )
            provider_record_id = _ipe_record_id(
                protocol=protocol,
                version=version,
                cvm_code=cvm_code,
                cnpj=cnpj,
                reference_date=reference_date,
                category=category,
                document_url=document_url,
            )

            records.append(
                CvmOpenDataIpeRecord(
                    provider_record_id=provider_record_id,
                    cnpj=cnpj,
                    cvm_code=cvm_code,
                    company_name=_clean(
                        _value(
                            row,
                            "nome_companhia",
                            "denom_cia",
                            "denom_social",
                        )
                    ),
                    reference_date=reference_date,
                    category=category,
                    disclosure_type=_clean(_value(row, "tipo")),
                    species=_clean(_value(row, "especie", "espécie")),
                    subject=_clean(_value(row, "assunto")),
                    delivered_at=delivered_at,
                    presentation_type=_clean(
                        _value(row, "tipo_apresentacao", "tipo_apresentação")
                    ),
                    protocol=protocol,
                    version=version,
                    document_url=document_url,
                    retrieved_at=retrieved_at,
                    raw_row=row,
                )
            )

        return CvmOpenDataIpeResult(
            year=year,
            source_url=url,
            retrieved_at=retrieved_at,
            records=tuple(records),
        )

    def fetch_issuers(self) -> CvmOpenDataIssuerResult:
        payload, retrieved_at = self._download(self.cad_url)
        rows = _read_csv(payload)

        issuers: list[CvmOpenDataIssuerRecord] = []
        for row in rows:
            legal_name = _clean(
                _value(row, "denom_social", "denominacao_social", "nome_companhia")
            )
            if not legal_name:
                continue
            issuers.append(
                CvmOpenDataIssuerRecord(
                    cvm_code=_normalize_cvm_code(
                        _value(row, "cd_cvm", "codigo_cvm")
                    ),
                    cnpj=_normalize_cnpj(_value(row, "cnpj_cia", "cnpj_companhia")),
                    legal_name=legal_name,
                    trading_name=_clean(
                        _value(row, "denom_comerc", "denominacao_comercial", "nome_pregao")
                    ),
                    registration_status=_clean(
                        _value(row, "sit", "situacao", "situacao_registro")
                    ),
                    retrieved_at=retrieved_at,
                    raw_row=row,
                )
            )

        return CvmOpenDataIssuerResult(
            source_url=self.cad_url,
            retrieved_at=retrieved_at,
            issuers=tuple(issuers),
        )

    def fetch_fca_securities(self, year: int) -> CvmOpenDataSecurityResult:
        _validate_year(year, minimum=2010)
        url = self.fca_url_template.format(year=year)
        payload, retrieved_at = self._download(url)
        rows = _read_zip_csv(
            payload,
            preferred_member=f"fca_cia_aberta_valor_mobiliario_{year}.csv",
            contains="valor_mobiliario",
        )

        securities: list[CvmOpenDataSecurityRecord] = []
        for row in rows:
            ticker = _normalize_ticker(
                _value(
                    row,
                    "codigo_negociacao",
                    "codigo_de_negociacao",
                    "cod_negociacao",
                    "ticker",
                )
            )
            if not ticker:
                continue
            securities.append(
                CvmOpenDataSecurityRecord(
                    cnpj=_normalize_cnpj(
                        _value(row, "cnpj_companhia", "cnpj_cia")
                    ),
                    company_name=_clean(
                        _value(row, "nome_companhia", "denom_cia", "denom_social")
                    ),
                    reference_date=_parse_date(
                        _value(row, "data_referencia", "dt_refer")
                    ),
                    ticker=ticker,
                    security_type=_clean(
                        _value(
                            row,
                            "tipo_valor_mobiliario",
                            "tipo_valor_mobiliário",
                            "tipo_ativo",
                        )
                    ),
                    security_description=_clean(
                        _value(
                            row,
                            "valor_mobiliario",
                            "valor_mobiliário",
                            "descricao_valor_mobiliario",
                            "descricao",
                        )
                    ),
                    market=_clean(_value(row, "mercado")),
                    exchange=_clean(
                        _value(
                            row,
                            "sigla_entidade_administradora",
                            "entidade_administradora",
                            "bolsa",
                        )
                    ),
                    trading_start=_parse_date(
                        _value(
                            row,
                            "data_inicio_negociacao",
                            "data_início_negociação",
                            "dt_inicio_negociacao",
                        )
                    ),
                    trading_end=_parse_date(
                        _value(
                            row,
                            "data_fim_negociacao",
                            "dt_fim_negociacao",
                        )
                    ),
                    retrieved_at=retrieved_at,
                    raw_row=row,
                )
            )

        return CvmOpenDataSecurityResult(
            year=year,
            source_url=url,
            retrieved_at=retrieved_at,
            securities=tuple(securities),
        )

    def _download(self, url: str) -> tuple[bytes, datetime]:
        request = urllib.request.Request(
            url,
            method="GET",
            headers={
                "Accept": "text/csv,application/zip,application/octet-stream,*/*",
                "User-Agent": self.user_agent,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = response.read()
        except Exception as exc:
            raise CvmOpenDataError(f"failed to download official CVM dataset: {url}") from exc

        if not payload:
            raise CvmOpenDataError(f"official CVM dataset was empty: {url}")
        return payload, datetime.now(timezone.utc)


def _read_zip_csv(
    payload: bytes,
    *,
    preferred_member: str,
    contains: str | None = None,
) -> list[dict[str, str]]:
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            members = [
                name
                for name in archive.namelist()
                if not name.endswith("/") and name.lower().endswith(".csv")
            ]
            if not members:
                raise CvmOpenDataError("official CVM ZIP contains no CSV files")

            preferred_lower = preferred_member.lower()
            chosen = next(
                (name for name in members if name.lower().endswith(preferred_lower)),
                None,
            )
            if chosen is None and contains:
                token = contains.lower()
                chosen = next(
                    (name for name in members if token in name.lower()),
                    None,
                )
            if chosen is None and len(members) == 1:
                chosen = members[0]
            if chosen is None:
                raise CvmOpenDataError(
                    f"expected CVM CSV member not found: {preferred_member}"
                )
            return _read_csv(archive.read(chosen))
    except zipfile.BadZipFile as exc:
        raise CvmOpenDataError("invalid CVM Open Data ZIP payload") from exc


def _read_csv(payload: bytes) -> list[dict[str, str]]:
    text: str | None = None
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            text = payload.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise CvmOpenDataError("unable to decode CVM CSV payload")

    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    if not reader.fieldnames:
        raise CvmOpenDataError("CVM CSV has no header")

    rows: list[dict[str, str]] = []
    for original in reader:
        normalized: dict[str, str] = {}
        for key, value in original.items():
            if key is None:
                continue
            normalized[_header_key(key)] = (value or "").strip()
        rows.append(normalized)
    return rows


def _value(row: dict[str, str], *names: str) -> str | None:
    for name in names:
        value = row.get(_header_key(name))
        if value is not None and value.strip():
            return value.strip()
    return None


def _header_key(value: str) -> str:
    text = unicodedata.normalize("NFKD", value)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold().strip()
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def _normalize_text(value: str) -> str:
    return _header_key(value).replace("_", " ")


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


def _normalize_cnpj(value: str | None) -> str | None:
    if not value:
        return None
    digits = re.sub(r"\D", "", value)
    return digits or None


def _normalize_cvm_code(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip()
    if text.endswith(".0"):
        text = text[:-2]
    digits = re.sub(r"\D", "", text)
    if not digits:
        return None
    return digits.lstrip("0") or "0"


def _normalize_ticker(value: str | None) -> str | None:
    if not value:
        return None
    ticker = value.strip().upper()
    ticker = re.sub(r"\s+", "", ticker)
    return ticker or None


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    text = value.strip()
    for fmt in (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
    ):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        pass

    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%Y-%m-%d",
        "%d/%m/%Y",
    ):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _ipe_record_id(
    *,
    protocol: str | None,
    version: str | None,
    cvm_code: str | None,
    cnpj: str | None,
    reference_date: date | None,
    category: str | None,
    document_url: str | None,
) -> str:
    if protocol:
        return "|".join(
            [
                "CVM_OPEN_DATA_IPE",
                protocol,
                version or "",
            ]
        )

    stable = "|".join(
        [
            cvm_code or "",
            cnpj or "",
            reference_date.isoformat() if reference_date else "",
            category or "",
            document_url or "",
            version or "",
        ]
    )
    digest = hashlib.sha256(stable.encode("utf-8")).hexdigest()
    return f"CVM_OPEN_DATA_IPE|sha256:{digest}"


def _validate_year(year: int, *, minimum: int) -> None:
    if not isinstance(year, int):
        raise TypeError("year must be int")
    current = datetime.now(timezone.utc).year
    if year < minimum or year > current + 1:
        raise ValueError(f"year must be between {minimum} and {current + 1}")
