"""Windows desktop entry point for the bundled B3 FastAPI orchestrator.

The Tauri shell launches this executable as a local sidecar. Importing the
FastAPI app directly keeps the application graph visible to PyInstaller.
"""

from __future__ import annotations

import os

import uvicorn

from b3_agent.server import app


def main() -> None:
    host = os.getenv("B3_AGENT_HOST", "127.0.0.1")
    port = int(os.getenv("B3_AGENT_PORT", "8000"))
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=os.getenv("B3_AGENT_LOG_LEVEL", "info"),
    )


if __name__ == "__main__":
    main()
