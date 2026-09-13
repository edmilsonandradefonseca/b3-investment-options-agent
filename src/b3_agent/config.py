from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    environment: str
    timezone: str
    project_root: Path
    data_dir: Path
    logs_dir: Path
    obsidian_vault: Path | None
    llm_enabled: bool
    llm_model: str
    max_llm_cost_usd: float


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)

    if value is None:
        return default

    return float(value)


def load_settings() -> Settings:
    project_root = Path(
        os.getenv(
            "B3_AGENT_PROJECT_ROOT",
            Path(__file__).resolve().parents[2],
        )
    ).resolve()

    data_dir = Path(
        os.getenv("B3_AGENT_DATA_DIR", project_root / "data")
    ).resolve()

    logs_dir = Path(
        os.getenv("B3_AGENT_LOGS_DIR", project_root / "logs")
    ).resolve()

    obsidian_value = os.getenv("B3_AGENT_OBSIDIAN_VAULT")

    obsidian_vault = (
        Path(obsidian_value).expanduser().resolve()
        if obsidian_value
        else None
    )

    return Settings(
        environment=os.getenv("B3_AGENT_ENV", "development"),
        timezone=os.getenv("B3_AGENT_TIMEZONE", "America/Sao_Paulo"),
        project_root=project_root,
        data_dir=data_dir,
        logs_dir=logs_dir,
        obsidian_vault=obsidian_vault,
        llm_enabled=_get_bool("B3_AGENT_LLM_ENABLED", False),
        llm_model=os.getenv("B3_AGENT_LLM_MODEL", "gpt-5.6-luna"),
        max_llm_cost_usd=_get_float(
            "B3_AGENT_MAX_LLM_COST_USD",
            1.00,
        ),
    )


settings = load_settings()
