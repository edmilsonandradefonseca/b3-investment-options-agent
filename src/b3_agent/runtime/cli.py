from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .manager import RuntimeManager


def _manager() -> RuntimeManager:
    root = Path(
        os.getenv("B3_RUNTIME_ROOT", "/opt/b3-runtime")
    ).expanduser()
    return RuntimeManager(root)


def _print(result: dict) -> None:
    print(json.dumps(result, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="b3-runtime",
        description="B3 Investment & Options Agent Runtime",
    )

    parser.add_argument(
        "command",
        choices=("start", "stop", "restart", "status", "health", "doctor"),
    )

    args = parser.parse_args()
    manager = _manager()

    try:
        if args.command == "start":
            _print(manager.start())
        elif args.command == "stop":
            _print(manager.stop())
        elif args.command == "restart":
            _print(manager.restart())
        elif args.command == "status":
            _print(manager.status())
        elif args.command == "health":
            _print(manager.health())
        elif args.command == "doctor":
            _print(manager.doctor())
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
