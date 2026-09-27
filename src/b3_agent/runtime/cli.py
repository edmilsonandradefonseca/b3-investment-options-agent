from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from urllib.error import URLError
from urllib.request import urlopen

from b3_agent.runtime.manager import RuntimeManager

SERVICE = "b3-runtime.service"


def _systemctl(action: str) -> int:
    cmd = ["systemctl", action, SERVICE]
    if os.geteuid() != 0 and shutil.which("sudo"):
        cmd.insert(0, "sudo")
    return subprocess.call(cmd)


def _health(manager: RuntimeManager) -> int:
    try:
        with urlopen(manager.local_health_url, timeout=5) as response:
            body = response.read().decode("utf-8")
            print(body)
            return 0 if 200 <= response.status < 300 else 1
    except (URLError, TimeoutError, OSError) as exc:
        print(f"health failed: {exc}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    args = list(argv or sys.argv[1:])
    command = args[0] if args else "status"
    manager = RuntimeManager()

    if command == "status":
        print(manager.format_status())
        return 0 if manager.status()["health"] == "ok" else 1
    if command == "health":
        return _health(manager)
    if command == "doctor":
        report = manager.doctor()
        print(manager.format_doctor())
        return 0 if report["status"] == "ok" else 1
    if command in {"start", "stop", "restart"}:
        return _systemctl(command)
    if command == "json":
        print(json.dumps(manager.status(), indent=2, sort_keys=True))
        return 0

    print("Usage: b3-runtime {status|health|doctor|start|stop|restart|json}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
