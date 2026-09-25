from __future__ import annotations

import os

import uvicorn


def main() -> None:
    host = os.getenv("B3_AGENT_HOST", "127.0.0.1")
    port = int(os.getenv("B3_AGENT_PORT", "8000"))
    uvicorn.run(
        "b3_agent.server:app",
        host=host,
        port=port,
        log_level=os.getenv("B3_AGENT_LOG_LEVEL", "info"),
    )


if __name__ == "__main__":
    main()
