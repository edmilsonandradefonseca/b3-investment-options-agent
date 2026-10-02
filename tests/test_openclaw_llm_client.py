from __future__ import annotations

from types import SimpleNamespace

from b3_agent.llm.client import OpenClawStructuredClient


def test_openclaw_structured_client_invokes_isolated_agent(monkeypatch):
    seen = {}

    def fake_run(command, input, capture_output, text, timeout):
        seen["command"] = command
        seen["input"] = input
        seen["timeout"] = timeout
        return SimpleNamespace(
            returncode=0,
            stdout='{"summary":"ok","items":[]}',
            stderr="",
        )

    monkeypatch.setattr("b3_agent.llm.client.subprocess.run", fake_run)

    client = OpenClawStructuredClient(
        agent="b3-investment",
        model="openai/gpt-5.6-luna",
        timeout=42,
        executable="/usr/bin/openclaw-test",
    )
    result = client.complete_json(
        instructions="Use supplied facts only.",
        input_text='{"ticker":"PETR4","evidence":"' + ("x" * 256_000) + '"}',
        schema_name="test_schema",
        schema={
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "items": {"type": "array"},
            },
            "required": ["summary", "items"],
        },
    )

    assert result == {"summary": "ok", "items": []}
    assert seen["timeout"] == 42
    command = seen["command"]
    assert command[:5] == [
        "/usr/bin/openclaw-test",
        "agent",
        "--agent",
        "b3-investment",
        "--model",
    ]
    assert "openai/gpt-5.6-luna" in command
    assert "--session-key" in command
    assert command[command.index("--session-key") + 1].startswith("b3-test_schema-")
    assert command[command.index("--message-file") + 1] == "-"
    assert len(" ".join(command)) < 1_000
    assert len(seen["input"]) > 250_000
    assert '"ticker":"PETR4"' in seen["input"]


def test_openclaw_structured_client_extracts_fenced_json():
    payload = OpenClawStructuredClient._extract_json(
        'prefix\n```json\n{"status":"ok"}\n```\nsuffix'
    )
    assert payload == {"status": "ok"}
