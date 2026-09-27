from __future__ import annotations

from b3_agent.runtime.manager import RuntimeManager


def main() -> int:
    return RuntimeManager().run_foreground()


if __name__ == "__main__":
    raise SystemExit(main())
