from __future__ import annotations

from io import BytesIO
import json
from urllib.error import HTTPError

import pytest

from b3_agent.providers.dadosdemercado_investors import (
    DadosDeMercadoInvestorsAdapter,
    InvestorFlowProviderError,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload


def test_adapter_maps_foreign_flow_without_inventing_unit():
    seen = {}

    def opener(request, timeout):
        seen["authorization"] = request.get_header("Authorization")
        seen["timeout"] = timeout
        return FakeResponse(
            [
                {
                    "date": "2026-09-24",
                    "foreigners": 91080000,
                    "institutional": -12600000,
                    "individuals": 450990000,
                }
            ]
        )

    records = DadosDeMercadoInvestorsAdapter(
        "test-token", opener=opener
    ).get_history()

    assert seen == {"authorization": "Bearer test-token", "timeout": 20}
    foreign = next(item for item in records if item.investor_type == "FOREIGN")
    assert foreign.net_financial_value == 91080000
    assert foreign.observation_date.isoformat() == "2026-09-24"
    assert foreign.source_record_id.endswith(":foreigners")
    assert foreign.quality_status == "WARNING"
    assert "provider_unit_not_declared" in foreign.quality_flags


def test_missing_token_returns_actionable_provider_state():
    with pytest.raises(InvestorFlowProviderError) as raised:
        DadosDeMercadoInvestorsAdapter("").get_history()
    assert raised.value.code == "CREDENTIAL_MISSING"


def test_rate_limit_is_not_reported_as_empty_data():
    def opener(request, timeout):
        raise HTTPError(request.full_url, 429, "rate limited", {}, BytesIO(b""))

    with pytest.raises(InvestorFlowProviderError) as raised:
        DadosDeMercadoInvestorsAdapter("test-token", opener=opener).get_history()
    assert raised.value.code == "RATE_LIMITED"
