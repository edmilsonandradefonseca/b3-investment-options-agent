from pathlib import Path

from b3_agent.config import settings


def health_check() -> dict[str, object]:
    """Check the basic health of the application environment."""
    checks: dict[str, bool] = {
        "project_root_exists": settings.project_root.exists(),
        "data_dir_available": _directory_available(settings.data_dir),
        "logs_dir_available": _directory_available(settings.logs_dir),
    }

    overall_status = "ok" if all(checks.values()) else "error"

    return {
        "status": overall_status,
        "service": "b3-investment-options-agent",
        "environment": settings.environment,
        "timezone": settings.timezone,
        "llm_enabled": settings.llm_enabled,
        "checks": checks,
    }


def _directory_available(path: Path) -> bool:
    """Create and verify a project directory."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        return path.is_dir()
    except OSError:
        return False


if __name__ == "__main__":
    result = health_check()

    print(f"Service:     {result['service']}")
    print(f"Status:      {result['status']}")
    print(f"Environment: {result['environment']}")
    print(f"Timezone:    {result['timezone']}")
    print(f"LLM enabled: {result['llm_enabled']}")
    print("Checks:")

    for name, passed in result["checks"].items():
        symbol = "OK" if passed else "FAIL"
        print(f"  [{symbol}] {name}")
