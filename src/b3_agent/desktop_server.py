"""Windows desktop entry point for the bundled B3 FastAPI orchestrator.

The Tauri shell launches this executable as a local sidecar. Keeping the
server entry point separate from server.py ensures Uvicorn actually starts.
"""

import uvicorn


if __name__ == "__main__":
    uvicorn.run(
        "b3_agent.server:app",
        host="127.0.0.1",
        port=8000,
        log_level="info",
    )
