from __future__ import annotations

import json
from io import BytesIO
from urllib.error import HTTPError

from b3_agent.llm import ollama_client as module
from b3_agent.llm.ollama_client import OllamaClient


class _Response:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_ollama_client_uses_bounded_defaults_and_exposes_timings(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["timeout"] = timeout
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return _Response(
            {
                "model": "deepseek-r1:8b",
                "message": {"content": "Concise analysis", "thinking": "x"},
                "total_duration": 100,
                "load_duration": 10,
                "prompt_eval_count": 120,
                "prompt_eval_cached_count": 0,
                "prompt_eval_duration": 20,
                "eval_count": 80,
                "eval_duration": 70,
            }
        )

    monkeypatch.delenv("B3_OLLAMA_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("B3_OLLAMA_NUM_CTX", raising=False)
    monkeypatch.delenv("B3_OLLAMA_NUM_PREDICT", raising=False)
    monkeypatch.delenv("B3_OLLAMA_KEEP_ALIVE", raising=False)
    monkeypatch.setattr(module, "urlopen", fake_urlopen)

    client = OllamaClient()
    result = client.ask("Analyze bounded evidence")

    assert captured["timeout"] == 300.0
    assert captured["payload"]["keep_alive"] == 0
    assert captured["payload"]["options"] == {
        "temperature": 0,
        "num_ctx": 2048,
        "num_predict": 768,
    }
    assert result.load_duration_ns == 10
    assert result.prompt_eval_count == 120
    assert result.prompt_eval_duration_ns == 20
    assert result.eval_count == 80
    assert result.eval_duration_ns == 70


def test_ollama_client_honors_runtime_bounds_from_environment(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["timeout"] = timeout
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return _Response(
            {
                "model": "deepseek-r1:8b",
                "message": {"content": "ok"},
            }
        )

    monkeypatch.setenv("B3_OLLAMA_TIMEOUT_SECONDS", "420")
    monkeypatch.setenv("B3_OLLAMA_NUM_CTX", "1536")
    monkeypatch.setenv("B3_OLLAMA_NUM_PREDICT", "256")
    monkeypatch.setenv("B3_OLLAMA_KEEP_ALIVE", "5m")
    monkeypatch.setattr(module, "urlopen", fake_urlopen)

    OllamaClient().ask("test")

    assert captured["timeout"] == 420.0
    assert captured["payload"]["keep_alive"] == "5m"
    assert captured["payload"]["options"]["num_ctx"] == 1536
    assert captured["payload"]["options"]["num_predict"] == 256


def test_ollama_timeout_error_includes_operational_bounds(monkeypatch):
    def fake_urlopen(request, timeout):
        raise TimeoutError("timed out")

    monkeypatch.setattr(module, "urlopen", fake_urlopen)

    client = OllamaClient(timeout=12, num_ctx=1024, num_predict=64)

    try:
        client.ask("test")
    except RuntimeError as exc:
        message = str(exc)
    else:
        raise AssertionError("expected RuntimeError")

    assert "model=deepseek-r1:8b" in message
    assert "timeout_s=12" in message
    assert "num_ctx=1024" in message
    assert "num_predict=64" in message
    assert "TimeoutError: timed out" in message


def test_ollama_client_can_disable_thinking_for_health_preflight(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return _Response(
            {
                "model": "deepseek-r1:8b",
                "message": {"content": "READY"},
            }
        )

    monkeypatch.setattr(module, "urlopen", fake_urlopen)

    OllamaClient(
        timeout=30,
        num_ctx=512,
        num_predict=24,
        keep_alive="5m",
        think=False,
    ).ask("Reply exactly READY.")

    assert captured["payload"]["think"] is False
    assert captured["payload"]["keep_alive"] == "5m"
    assert captured["payload"]["options"]["num_predict"] == 24


def test_ollama_client_sends_structured_output_schema(monkeypatch):
    captured = {}
    schema = {
        "type": "object",
        "properties": {"summary": {"type": "string"}},
        "required": ["summary"],
    }

    def fake_urlopen(request, timeout):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return _Response(
            {
                "model": "deepseek-r1:8b",
                "message": {"content": '{"summary":"ok"}'},
            }
        )

    monkeypatch.setattr(module, "urlopen", fake_urlopen)

    result = OllamaClient(
        timeout=30,
        num_ctx=512,
        num_predict=64,
        format_schema=schema,
    ).ask("Return JSON")

    assert captured["payload"]["format"] == schema
    assert result.content == '{"summary":"ok"}'


def test_ollama_client_retries_without_think_for_older_runtime(monkeypatch):
    payloads = []

    def fake_urlopen(request, timeout):
        payload = json.loads(request.data.decode("utf-8"))
        payloads.append(payload)
        if len(payloads) == 1:
            raise HTTPError(
                request.full_url,
                400,
                "Bad Request",
                hdrs=None,
                fp=BytesIO(b'{"error":"think is not supported by this runtime"}'),
            )
        return _Response(
            {
                "model": "deepseek-r1:8b",
                "message": {"content": '{"relevance":"UNKNOWN"}'},
            }
        )

    monkeypatch.setattr(module, "urlopen", fake_urlopen)

    result = OllamaClient(
        timeout=30,
        num_ctx=512,
        num_predict=64,
        think=False,
    ).ask("Return JSON")

    assert payloads[0]["think"] is False
    assert "think" not in payloads[1]
    assert result.content == '{"relevance":"UNKNOWN"}'


def test_ollama_http_error_includes_response_detail(monkeypatch):
    def fake_urlopen(request, timeout):
        raise HTTPError(
            request.full_url,
            500,
            "Internal Server Error",
            hdrs=None,
            fp=BytesIO(b'{"error":"model runner crashed"}'),
        )

    monkeypatch.setattr(module, "urlopen", fake_urlopen)

    try:
        OllamaClient(timeout=30, num_ctx=512, num_predict=64).ask("test")
    except RuntimeError as exc:
        message = str(exc)
    else:
        raise AssertionError("expected RuntimeError")

    assert "HTTPError 500" in message
    assert "model runner crashed" in message
