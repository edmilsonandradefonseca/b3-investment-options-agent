from __future__ import annotations

from datetime import date, datetime, time, timezone
import json
import urllib.parse
import urllib.request

from b3_agent.schemas.macro import MacroObservation


class BcbSgsAdapter:
    """Banco Central do Brasil SGS adapter for structured macro observations."""

    BASE_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs"

    SERIES: dict[str, tuple[int, str]] = {
        "SELIC": (1178, "percent_per_year"),
        "CDI": (12, "percent_per_day"),
        "IPCA": (433, "percent_per_month"),
    }

    @property
    def name(self) -> str:
        return "bcb_sgs"

    def get_series(
        self,
        indicator: str,
        *,
        start: date,
        end: date,
    ) -> list[MacroObservation]:
        normalized = indicator.upper().strip()
        if normalized not in self.SERIES:
            raise ValueError(f"unsupported BCB SGS indicator: {indicator}")
        if start > end:
            raise ValueError("start date must be on or before end date")

        series_id, unit = self.SERIES[normalized]
        params = urllib.parse.urlencode(
            {
                "formato": "json",
                "dataInicial": start.strftime("%d/%m/%Y"),
                "dataFinal": end.strftime("%d/%m/%Y"),
            }
        )
        url = f"{self.BASE_URL}.{series_id}/dados?{params}"
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "b3-investment-options-agent/0.1",
                "Accept": "application/json",
            },
        )

        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))

        if not isinstance(payload, list):
            raise ValueError(f"BCB SGS returned invalid payload for {normalized}")

        ingested_at = datetime.now(timezone.utc)
        records: list[MacroObservation] = []
        for item in payload:
            raw_date = item.get("data")
            raw_value = item.get("valor")
            if raw_date in (None, "") or raw_value in (None, ""):
                continue
            observed_date = datetime.strptime(str(raw_date), "%d/%m/%Y").date()
            observed_at = datetime.combine(
                observed_date,
                time.min,
                tzinfo=timezone.utc,
            )
            value = float(str(raw_value).replace(",", "."))
            records.append(
                MacroObservation(
                    instrument_id=f"MACRO-{normalized}",
                    ticker=normalized,
                    observation_timestamp=observed_at,
                    available_timestamp=ingested_at,
                    source=self.name,
                    ingested_at=ingested_at,
                    source_record_id=f"sgs:{series_id}:{observed_date.isoformat()}",
                    quality_status="WARNING",
                    quality_flags=("availability_is_ingestion_time",),
                    indicator=normalized,
                    value=value,
                    unit=unit,
                    reference_period=observed_date.isoformat(),
                )
            )

        if not records:
            raise ValueError(
                f"BCB SGS returned no observations for {normalized} "
                f"between {start.isoformat()} and {end.isoformat()}"
            )
        return records

    def latest(
        self,
        indicator: str,
        *,
        start: date,
        end: date,
    ) -> MacroObservation:
        records = self.get_series(indicator, start=start, end=end)
        return max(records, key=lambda item: item.observation_timestamp)

    def get_core_snapshot(
        self,
        *,
        start: date,
        end: date,
    ) -> dict[str, MacroObservation]:
        return {
            indicator: self.latest(indicator, start=start, end=end)
            for indicator in ("SELIC", "CDI", "IPCA")
        }
