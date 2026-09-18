from __future__ import annotations

from typing import Any, Protocol

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


class OpenAIResponsesClient:
    """OpenAI Responses API adapter for structured agent output."""

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

        import json

        return json.loads(response.output_text)
