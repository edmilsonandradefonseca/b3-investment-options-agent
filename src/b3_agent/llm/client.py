from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
from typing import Any, Protocol
from uuid import uuid4

from openai import OpenAI


class LLMClient(Protocol):
    """Minimal interface used by agents; keeps orchestration model-agnostic."""

    def complete_json(
        self,
        *,
        instructions: str,
        input_text: str,
        schema_name: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]: ...


class OpenClawStructuredClient:
    """Structured LLM adapter backed by an isolated OpenClaw agent.

    The B3 runtime uses this adapter for senior reasoning so OpenAI access is
    mediated by OpenClaw/OAuth rather than by a direct paid API key. Each
    request receives an isolated session key to avoid cross-request memory
    leakage. Canonical numerical authority remains outside this client.
    """

    def __init__(
        self,
        *,
        agent: str = "b3-investment",
        model: str = "openai/gpt-5.6-luna",
        timeout: float = 180.0,
        executable: str | None = None,
    ):
        self.agent = agent
        self.model = model
        self.timeout = timeout
        self.executable = self._resolve_executable(executable)

    @staticmethod
    def _resolve_executable(executable: str | None) -> str:
        if executable:
            return executable

        discovered = shutil.which("openclaw")
        if discovered:
            return discovered

        user_install = Path.home() / ".npm-global" / "bin" / "openclaw"
        if user_install.is_file():
            return str(user_install)

        raise RuntimeError(
            "OpenClaw executable not found; set B3_OPENCLAW_BIN or install openclaw"
        )

    @staticmethod
    def _extract_json(response: str) -> dict[str, Any]:
        text = response.strip()

        try:
            payload = json.loads(text)
            if isinstance(payload, dict):
                return payload
        except json.JSONDecodeError:
            pass

        if "```" in text:
            for block in text.split("```"):
                candidate = block.strip()
                if candidate.lower().startswith("json"):
                    candidate = candidate[4:].strip()
                try:
                    payload = json.loads(candidate)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict):
                    return payload

        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                payload = json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                payload = None
            if isinstance(payload, dict):
                return payload

        raise RuntimeError("OpenClaw response did not contain a valid JSON object")

    def complete_json(
        self,
        *,
        instructions: str,
        input_text: str,
        schema_name: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        prompt = (
            f"{instructions}\n\n"
            "Return ONLY one valid JSON object. Do not use Markdown fences or prose. "
            f"The object must match the JSON Schema named {schema_name!r}.\n"
            f"JSON Schema:\n{json.dumps(schema, ensure_ascii=False)}\n\n"
            f"Input:\n{input_text}"
        )
        session_key = f"b3-{schema_name}-{uuid4().hex}"
        command = [
            self.executable,
            "agent",
            "--agent",
            self.agent,
            "--model",
            self.model,
            "--session-key",
            session_key,
            "--message",
            prompt,
        ]

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"OpenClaw timed out after {self.timeout:.0f}s for {schema_name}"
            ) from exc
        except OSError as exc:
            raise RuntimeError(
                f"OpenClaw launch failed for {schema_name}: "
                f"{type(exc).__name__}: {exc}"
            ) from exc

        if result.returncode != 0:
            message = (
                result.stderr.strip()
                or result.stdout.strip()
                or f"OpenClaw exited with code {result.returncode}"
            )
            raise RuntimeError(message)

        if not result.stdout.strip():
            raise RuntimeError("OpenClaw returned an empty response")

        return self._extract_json(result.stdout)


class OpenAIResponsesClient:
    """Direct OpenAI Responses API adapter.

    This path is retained only as an explicitly enabled fallback. Production
    defaults to OpenClawStructuredClient.
    """

    def __init__(self, *, model: str = "gpt-5.6-luna", client: OpenAI | None = None):
        self.model = model
        self.client = client or OpenAI()

    def complete_json(
        self,
        *,
        instructions: str,
        input_text: str,
        schema_name: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        response = self.client.responses.create(
            model=self.model,
            instructions=instructions,
            input=input_text,
            text={
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "schema": schema,
                    "strict": True,
                }
            },
        )

        return json.loads(response.output_text)
