from __future__ import annotations

from types import SimpleNamespace

from b3_agent.llm import ollama_runtime as runtime


class FakeWarmClient:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def ask(self, prompt):
        assert prompt == "Reply exactly READY."
        return SimpleNamespace(
            model="deepseek-r1:8b",
            content="READY",
            load_duration_ns=10,
            prompt_eval_count=4,
            eval_count=1,
            eval_duration_ns=5,
        )


def test_ollama_preflight_validates_model_and_warms_it(monkeypatch):
    calls = []

    def fake_get_json(url, *, timeout):
        calls.append((url, timeout))
        if url.endswith("/api/tags"):
            return {"models": [{"name": "deepseek-r1:8b"}]}
        if url.endswith("/api/ps"):
            return {"models": [{"name": "deepseek-r1:8b"}]}
        raise AssertionError(url)

    monkeypatch.setattr(runtime, "_get_json", fake_get_json)
    monkeypatch.setattr(runtime, "OllamaClient", FakeWarmClient)

    base = SimpleNamespace(
        base_url="http://127.0.0.1:11434",
        model="deepseek-r1:8b",
        timeout=300.0,
    )
    result = runtime.ollama_preflight(client=base)

    assert result.model == "deepseek-r1:8b"
    assert result.response == "READY"
    assert result.installed_models == ("deepseek-r1:8b",)
    assert result.loaded_models_after == ("deepseek-r1:8b",)
    assert calls[0][0].endswith("/api/tags")
    assert calls[-1][0].endswith("/api/ps")


def test_ollama_preflight_fails_before_generation_when_model_missing(monkeypatch):
    monkeypatch.setattr(
        runtime,
        "_get_json",
        lambda url, timeout: {"models": [{"name": "qwen3:8b"}]},
    )

    base = SimpleNamespace(
        base_url="http://127.0.0.1:11434",
        model="deepseek-r1:8b",
        timeout=300.0,
    )

    try:
        runtime.ollama_preflight(client=base)
    except RuntimeError as exc:
        message = str(exc)
    else:
        raise AssertionError("expected RuntimeError")

    assert "not installed" in message
    assert "deepseek-r1:8b" in message
    assert "qwen3:8b" in message


def test_model_available_accepts_latest_alias():
    assert runtime._model_available(
        "deepseek-r1",
        ("deepseek-r1:latest",),
    )
    assert not runtime._model_available(
        "deepseek-r1:8b",
        ("deepseek-r1:latest",),
    )
