from __future__ import annotations

from unittest.mock import patch

from b3_agent.llm.client import OpenClawStructuredClient


def test_openclaw_os_launch_failure_becomes_runtime_error():
    client = OpenClawStructuredClient(
        executable="/usr/bin/false",
        timeout=1,
    )
    with patch(
        "b3_agent.llm.client.subprocess.run",
        side_effect=OSError(7, "Argument list too long"),
    ):
        try:
            client.complete_json(
                instructions="test",
                input_text="payload",
                schema_name="test_schema",
                schema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            )
        except RuntimeError as exc:
            message = str(exc)
            assert "OpenClaw launch failed" in message
            assert "Argument list too long" in message
        else:
            raise AssertionError("OSError must be converted to RuntimeError")
