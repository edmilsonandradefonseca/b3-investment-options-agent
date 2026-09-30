from __future__ import annotations

from types import SimpleNamespace

from b3_agent.llm import ollama_runtime as runtime


def test_ollama_preflight_uses_empty_chat_preload_and_accepts_empty_content(monkeypatch):
    get_calls = []
    post_calls = []
    ps_count = 0

    def fake_get_json(url, *, timeout):
        nonlocal ps_count
        get_calls.append((url, timeout))
        if url.endswith("/api/version"):
            return {"version": "0.12.0"}
        if url.endswith("/api/tags"):
            return {"models": [{"name": "deepseek-r1:8b"}]}
        if url.endswith("/api/ps"):
            ps_count += 1
            if ps_count == 1:
                return {"models": []}
            return {"models": [{"name": "deepseek-r1:8b"}]}
        raise AssertionError(url)

    def fake_post_json(url, payload, *, timeout):
        post_calls.append((url, payload, timeout))
        return {
            "model": "deepseek-r1:8b",
            "message": {"role": "assistant", "content": ""},
            "done": True,
            "done_reason": "load",
            "load_duration": 123,
        }

    monkeypatch.setattr(runtime, "_get_json", fake_get_json)
    monkeypatch.setattr(runtime, "_post_json", fake_post_json)

    base = SimpleNamespace(
        base_url="http://127.0.0.1:11434",
        model="deepseek-r1:8b",
        timeout=300.0,
    )
    result = runtime.ollama_preflight(client=base)

    assert result.model == "deepseek-r1:8b"
    assert result.ollama_version == "0.12.0"
    assert result.done is True
    assert result.done_reason == "load"
    assert result.load_duration_ns == 123
    assert result.installed_models == ("deepseek-r1:8b",)
    assert result.loaded_models_before == ()
    assert result.loaded_models_after == ("deepseek-r1:8b",)

    assert len(post_calls) == 1
    url, payload, timeout = post_calls[0]
    assert url.endswith("/api/chat")
    assert payload == {
        "model": "deepseek-r1:8b",
        "messages": [],
        "stream": False,
        "keep_alive": "5m",
    }
    assert timeout == 180.0
    assert get_calls[0][0].endswith("/api/version")
    assert get_calls[-1][0].endswith("/api/ps")


def test_ollama_preflight_fails_before_preload_when_model_missing(monkeypatch):
    def fake_get_json(url, *, timeout):
        if url.endswith("/api/version"):
            return {"version": "0.12.0"}
        if url.endswith("/api/tags"):
            return {"models": [{"name": "qwen3:8b"}]}
        raise AssertionError(url)

    monkeypatch.setattr(runtime, "_get_json", fake_get_json)

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


def test_ollama_preflight_requires_model_to_be_resident_after_load(monkeypatch):
    def fake_get_json(url, *, timeout):
        if url.endswith("/api/version"):
            return {"version": "0.12.0"}
        if url.endswith("/api/tags"):
            return {"models": [{"name": "deepseek-r1:8b"}]}
        if url.endswith("/api/ps"):
            return {"models": []}
        raise AssertionError(url)

    monkeypatch.setattr(runtime, "_get_json", fake_get_json)
    monkeypatch.setattr(
        runtime,
        "_post_json",
        lambda url, payload, timeout: {
            "model": "deepseek-r1:8b",
            "message": {"role": "assistant", "content": ""},
            "done": True,
            "done_reason": "load",
        },
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

    assert "not resident" in message


def test_ollama_preflight_rejects_incomplete_load_response(monkeypatch):
    ps_count = 0

    def fake_get_json(url, *, timeout):
        nonlocal ps_count
        if url.endswith("/api/version"):
            return {"version": "0.12.0"}
        if url.endswith("/api/tags"):
            return {"models": [{"name": "deepseek-r1:8b"}]}
        if url.endswith("/api/ps"):
            ps_count += 1
            return {"models": []}
        raise AssertionError(url)

    monkeypatch.setattr(runtime, "_get_json", fake_get_json)
    monkeypatch.setattr(
        runtime,
        "_post_json",
        lambda url, payload, timeout: {
            "model": "deepseek-r1:8b",
            "done": False,
        },
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

    assert "did not complete" in message


def test_model_available_accepts_latest_alias():
    assert runtime._model_available(
        "deepseek-r1",
        ("deepseek-r1:latest",),
    )
    assert not runtime._model_available(
        "deepseek-r1:8b",
        ("deepseek-r1:latest",),
    )
