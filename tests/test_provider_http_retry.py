from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request

import pytest

from b3_agent.providers.http_retry import ProviderRequestError, request_json


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_request_json_retries_transient_timeout(monkeypatch):
    monkeypatch.setenv("B3_PROVIDER_RETRY_DELAY_SECONDS", "0")
    calls = []

    def opener(request, timeout):
        calls.append(timeout)
        if len(calls) == 1:
            raise TimeoutError("temporary")
        return FakeResponse({"ok": True})

    payload = request_json(
        Request("https://example.invalid"),
        provider="test",
        timeout_env="B3_TEST_TIMEOUT",
        default_timeout=7,
        default_attempts=2,
        opener=opener,
    )

    assert payload == {"ok": True}
    assert calls == [7.0, 7.0]


def test_request_json_retries_configured_http_status(monkeypatch):
    monkeypatch.setenv("B3_PROVIDER_RETRY_DELAY_SECONDS", "0")
    calls = []

    def opener(request, timeout):
        calls.append(timeout)
        if len(calls) == 1:
            raise HTTPError(request.full_url, 404, "not found", {}, None)
        return FakeResponse({"results": [1]})

    payload = request_json(
        Request("https://example.invalid"),
        provider="brapi",
        timeout_env="B3_TEST_TIMEOUT",
        default_timeout=5,
        retry_http_codes={404},
        default_attempts=2,
        opener=opener,
    )
    assert payload == {"results": [1]}
    assert len(calls) == 2


def test_request_json_does_not_retry_non_retryable_auth_error(monkeypatch):
    monkeypatch.setenv("B3_PROVIDER_RETRY_DELAY_SECONDS", "0")
    calls = []

    def opener(request, timeout):
        calls.append(timeout)
        raise HTTPError(request.full_url, 401, "unauthorized", {}, None)

    with pytest.raises(ProviderRequestError, match="HTTP 401 after 1 attempt"):
        request_json(
            Request("https://example.invalid"),
            provider="test",
            timeout_env="B3_TEST_TIMEOUT",
            default_timeout=5,
            retry_http_codes={429, 500},
            default_attempts=3,
            opener=opener,
        )
    assert len(calls) == 1


def test_request_json_reports_final_network_failure(monkeypatch):
    monkeypatch.setenv("B3_PROVIDER_RETRY_DELAY_SECONDS", "0")
    calls = []

    def opener(request, timeout):
        calls.append(timeout)
        raise URLError("offline")

    with pytest.raises(ProviderRequestError, match="after 2 attempt"):
        request_json(
            Request("https://example.invalid"),
            provider="test",
            timeout_env="B3_TEST_TIMEOUT",
            default_timeout=5,
            default_attempts=2,
            opener=opener,
        )
    assert len(calls) == 2
