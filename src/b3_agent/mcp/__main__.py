"""CLI entry point for the B3 MCP server."""

from .server import mcp


if __name__ == "__main__":
    mcp.run()
