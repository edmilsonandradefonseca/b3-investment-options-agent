from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from b3_agent.llm.client import OpenClawStructuredClient


def test_openclaw_structured_client_invokes_isolated_agent(monkeypatch):
    seen = {}

    def fake_run(command, capture_output, text, timeout):
        seen["command"] = command
        seen["timeout"] = timeout
        message_path = Path(command[command.index("--message-file") + 1])
        seen["message_path"] = message_path
        seen["input"] = message_path.read_text(encoding="utf-8")
        assert message_path.stat().st_mode & 0o077 == 0
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
    message_path = Path(command[command.index("--message-file") + 1])
    assert message_path.name.startswith("b3-openclaw-")
    assert len(" ".join(command)) < 1_000
    assert len(seen["input"]) > 250_000
    assert '"ticker":"PETR4"' in seen["input"]
    assert not message_path.exists()


def test_openclaw_message_file_is_removed_when_process_launch_fails(monkeypatch):
    seen = {}

    def fake_run(command, capture_output, text, timeout):
        path = Path(command[command.index("--message-file") + 1])
        seen["path"] = path
        assert path.exists()
        raise OSError("launch failed")

    monkeypatch.setattr("b3_agent.llm.client.subprocess.run", fake_run)
    client = OpenClawStructuredClient(executable="/usr/bin/openclaw-test")

    try:
        client.complete_json(
            instructions="Return JSON.",
            input_text="{}",
            schema_name="test_schema",
            schema={"type": "object"},
        )
    except RuntimeError as exc:
        assert "launch failed" in str(exc)
    else:
        raise AssertionError("launch error was not raised")
    assert not seen["path"].exists()


def test_openclaw_structured_client_extracts_fenced_json():
    payload = OpenClawStructuredClient._extract_json(
        'prefix\n```json\n{"status":"ok"}\n```\nsuffix'
    )
    assert payload == {"status": "ok"}
