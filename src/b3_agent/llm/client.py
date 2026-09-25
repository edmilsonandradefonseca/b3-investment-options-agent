from __future__ import annotations

import json
import subprocess
from typing import Any, Protocol


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


class OpenClawInferenceClient:
    """B3 LLM adapter using OpenClaw's ChatGPT OAuth inference transport."""

    def __init__(
        self,
        *,
        model: str = "openai/gpt-5.6-luna",
        agent: str = "joao-resolve",
    ):
        self.model = model if "/" in model else f"openai/{model}"
        self.agent = agent

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
            "Return ONLY valid JSON matching this schema.\n"
            f"Schema name: {schema_name}\n"
            f"JSON Schema:\n{json.dumps(schema, ensure_ascii=False)}\n\n"
            f"Input:\n{input_text}"
        )

        result = subprocess.run(
            [
                "openclaw",
                "infer",
                "model",
                "run",
                "--agent",
                self.agent,
                "--model",
                self.model,
                "--prompt",
                prompt,
                "--json",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )

        if result.returncode != 0:
            raise RuntimeError(
                "OpenClaw inference failed: "
                f"exit={result.returncode}; stderr={result.stderr.strip()}"
            )

        try:
            envelope = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Invalid OpenClaw JSON response: {result.stdout[-2000:]}"
            ) from exc

        outputs = envelope.get("outputs") or []
        if not outputs or not outputs[0].get("text"):
            raise RuntimeError(f"OpenClaw returned no text output: {envelope}")

        text = outputs[0]["text"].strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Model returned invalid JSON for schema {schema_name}: {text}"
            ) from exc


# Backward-compatible name used by the existing B3 runtime.
OpenAIResponsesClient = OpenClawInferenceClient
