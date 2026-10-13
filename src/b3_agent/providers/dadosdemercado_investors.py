from __future__ import annotations

from datetime import date, datetime, time, timezone
from http.client import HTTPResponse
import json
import os
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from b3_agent.schemas.flow import FlowData


class InvestorFlowProviderError(RuntimeError):
    """Provider error with a stable code suitable for an API response."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class DadosDeMercadoInvestorsAdapter:
    """Fetches investor flow history from Dados de Mercado's authenticated API.

    The provider returns one numeric observation per investor category and date.
    The adapter preserves that reported value as net_financial_value and marks
    the unit as unverified because the documented API schema does not declare it.
    """

    BASE_URL = "https://api.dadosdemercado.com.br/v1/investors"
    SOURCE = "dadosdemercado"
    CATEGORY_FIELDS: dict[str, str] = {
        "foreigners": "FOREIGN",
        "institutional": "INSTITUTIONAL",
        "individuals": "INDIVIDUAL",
        "financial_institutions": "FINANCIAL_INSTITUTION",
        "companies": "COMPANY",
        "clubs": "INVESTMENT_CLUB",
        "other": "OTHER",
    }

    def __init__(
        self,
        token: str | None = None,
        *,
        timeout_seconds: float = 20,
        opener: Callable[..., HTTPResponse] = urlopen,
    ) -> None:
        self.token = (token if token is not None else os.getenv("DADOSDE_MERCADO_API_TOKEN", "")).strip()
        self.timeout_seconds = timeout_seconds
        self.opener = opener

    def get_history(self) -> list[FlowData]:
        if not self.token:
            raise InvestorFlowProviderError(
                "CREDENTIAL_MISSING",
                "DADOSDE_MERCADO_API_TOKEN não está configurado no backend.",
            )

        request = Request(
            self.BASE_URL,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
                "User-Agent": "b3-investment-options-agent/0.1",
            },
        )
        try:
            with self.opener(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code in (401, 403):
                raise InvestorFlowProviderError(
                    "CREDENTIAL_REJECTED",
                    "Dados de Mercado recusou a credencial (HTTP "
                    f"{exc.code}). Verifique token e permissões.",
                ) from exc
            if exc.code == 429:
                raise InvestorFlowProviderError(
                    "RATE_LIMITED",
                    "Limite de requisições da API Dados de Mercado atingido.",
                ) from exc
            raise InvestorFlowProviderError(
                "PROVIDER_HTTP_ERROR",
                f"Dados de Mercado respondeu HTTP {exc.code}.",
            ) from exc
        except (TimeoutError, URLError, OSError) as exc:
            raise InvestorFlowProviderError(
                "PROVIDER_UNAVAILABLE",
                "Não foi possível consultar a API Dados de Mercado.",
            ) from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise InvestorFlowProviderError(
                "INVALID_RESPONSE",
                "A API Dados de Mercado retornou JSON inválido.",
            ) from exc

        rows = payload.get("data") if isinstance(payload, dict) else payload
        if not isinstance(rows, list):
            raise InvestorFlowProviderError(
                "INVALID_RESPONSE",
                "A API Dados de Mercado não retornou uma lista de observações.",
            )

        ingested_at = datetime.now(timezone.utc)
        records: list[FlowData] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            observed_date = self._parse_date(row.get("date"))
            if observed_date is None:
                continue
            observed_at = datetime.combine(observed_date, time.min, tzinfo=timezone.utc)
            for field, investor_type in self.CATEGORY_FIELDS.items():
                raw_value = row.get(field)
                if raw_value is None:
                    continue
                value = self._number(raw_value)
                records.append(
                    FlowData(
                        instrument_id=f"B3-INVESTOR-FLOW-{investor_type}",
                        ticker="B3",
                        observation_timestamp=observed_at,
                        available_timestamp=ingested_at,
                        source=self.SOURCE,
                        ingested_at=ingested_at,
                        source_record_id=(
                            f"dadosdemercado:investors:{observed_date.isoformat()}:{field}"
                        ),
                        quality_status="WARNING",
                        quality_flags=("provider_unit_not_declared",),
                        investor_type=investor_type,
                        market_segment="B3",
                        net_financial_value=value,
                        observation_date=observed_date,
                    )
                )
        return records

    @staticmethod
    def _parse_date(raw: Any) -> date | None:
        if not isinstance(raw, str) or not raw.strip():
            return None
        value = raw.strip()
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            try:
                return datetime.strptime(value, "%d/%m/%Y").date()
            except ValueError:
                return None

    @staticmethod
    def _number(raw: Any) -> float:
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise InvestorFlowProviderError(
                "INVALID_RESPONSE",
                "A API Dados de Mercado retornou valor de fluxo não numérico.",
            )
        return float(raw)
