from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Callable
import io
import zipfile

import pyettj.ettj as pyettj_ettj
import requests

from b3_agent.schemas.yield_curve import YieldCurvePoint


class YieldCurveProviderError(RuntimeError):
    """Stable curve adapter errors suitable for an HTTP response."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class B3YieldCurveAdapter:
    """Downloads B3 TaxaSwap data with TLS verification and parses it via pyettj.

    pyettj 0.4.2's public B3 download function currently sets verify=False.
    This adapter uses its date/URL and parsing helpers, but performs the HTTPS
    request itself with certificate verification enabled.
    """

    SOURCE = "b3_taxaswap_pyettj"
    CURVES = {"PRE", "DIC", "DCL"}

    def __init__(
        self,
        *,
        timeout_seconds: float = 30,
        http_get: Callable[..., requests.Response] = requests.get,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.http_get = http_get

    def get_latest(self, curve: str = "PRE", *, as_of: date | None = None) -> list[YieldCurvePoint]:
        normalized_curve = curve.upper().strip()
        if normalized_curve not in self.CURVES:
            raise ValueError(f"unsupported yield curve code: {curve}")

        requested_date = as_of or date.today()
        last_no_data: Exception | None = None
        for days_back in range(8):
            reference_date = requested_date - timedelta(days=days_back)
            try:
                return self._get_for_date(normalized_curve, reference_date)
            except YieldCurveProviderError as exc:
                if exc.code != "NO_DATA":
                    raise
                last_no_data = exc
        raise YieldCurveProviderError(
            "NO_DATA",
            f"A curva {normalized_curve} não foi encontrada nos últimos 8 dias corridos.",
        ) from last_no_data

    def _get_for_date(self, curve: str, reference_date: date) -> list[YieldCurvePoint]:
        date_label = reference_date.strftime("%d/%m/%Y")
        try:
            url = pyettj_ettj._montar_url(reference_date)
            response = self.http_get(
                url,
                headers=pyettj_ettj._HEADERS_DEFAULT,
                timeout=self.timeout_seconds,
                verify=True,
            )
            response.raise_for_status()
            # B3 returns HTTP 200 and an empty ZIP before publication (and on
            # non-trading days). This is absence of a daily file, not corruption.
            # Only an actual empty ZIP permits fallback; malformed bytes still fail.
            if zipfile.is_zipfile(io.BytesIO(response.content)):
                with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
                    if not archive.namelist():
                        raise YieldCurveProviderError(
                            "NO_DATA", f"A B3 ainda não publicou TaxaSwap em {date_label}."
                        )
            text = pyettj_ettj._extrair_txt(response.content, date_label)
            frame = pyettj_ettj._parsear_txt(text, [curve], reference_date)
            pyettj_ettj._validar_output(frame, [curve], date_label)
        except YieldCurveProviderError:
            raise
        except Exception as exc:
            if type(exc).__name__ in {"NoDataError", "HolidayError", "DataNotAvailableError"}:
                raise YieldCurveProviderError(
                    "NO_DATA",
                    f"A B3 não publicou a curva {curve} em {date_label}.",
                ) from exc
            if isinstance(exc, requests.RequestException):
                raise YieldCurveProviderError(
                    "PROVIDER_UNAVAILABLE",
                    "Não foi possível consultar o arquivo TaxaSwap da B3.",
                ) from exc
            if isinstance(exc, ValueError):
                raise YieldCurveProviderError(
                    "INVALID_DATA",
                    "O arquivo TaxaSwap não contém uma curva válida.",
                ) from exc
            raise YieldCurveProviderError(
                "PROVIDER_ERROR",
                "Falha ao baixar ou interpretar a curva publicada pela B3.",
            ) from exc

        if frame.empty:
            raise YieldCurveProviderError(
                "NO_DATA",
                f"A B3 não publicou a curva {curve} em {date_label}.",
            )

        ingested_at = datetime.now(timezone.utc)
        records: list[YieldCurvePoint] = []
        for row in frame.itertuples(index=False):
            row_curve = str(row.curva).strip().upper()
            if row_curve != curve:
                continue
            days_calendar = int(row.dias_corridos)
            days_business = int(row.dias_uteis)
            rate = float(row.taxa)
            if days_calendar < 0 or days_business < 0 or not (-1 < rate < 10):
                raise YieldCurveProviderError(
                    "INVALID_DATA",
                    f"A B3 retornou vértice ou taxa inválidos para {curve}.",
                )
            description = str(getattr(row, "descricao", "")).strip()
            vertex = str(row.vertice).strip()
            observed_at = datetime.combine(reference_date, time.min, tzinfo=timezone.utc)
            records.append(
                YieldCurvePoint(
                    instrument_id=f"ETTJ-{curve}-{days_calendar}",
                    ticker=f"ETTJ-{curve}",
                    observation_timestamp=observed_at,
                    available_timestamp=ingested_at,
                    source=self.SOURCE,
                    ingested_at=ingested_at,
                    source_record_id=(
                        f"b3:taxaswap:{reference_date.isoformat()}:{curve}:{days_calendar}"
                    ),
                    quality_status="WARNING",
                    quality_flags=("availability_timestamp_is_ingestion_time",),
                    curve_code=curve,
                    curve_description=description or curve,
                    days_calendar=days_calendar,
                    days_business=days_business,
                    rate_decimal=rate,
                    vertex=vertex,
                )
            )
        if not records:
            raise YieldCurveProviderError(
                "NO_DATA",
                f"A B3 não retornou vértices para a curva {curve} em {date_label}.",
            )
        return records
