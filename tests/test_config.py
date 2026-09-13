from pathlib import Path

from b3_agent.config import Settings, load_settings


def test_load_settings_defaults():
    settings = load_settings()

    assert isinstance(settings, Settings)
    assert settings.environment == "development"
    assert settings.timezone == "America/Sao_Paulo"
    assert settings.llm_enabled is False
    assert settings.llm_model == "gpt-5.6-luna"
    assert settings.max_llm_cost_usd == 1.00
    assert isinstance(settings.project_root, Path)


def test_project_directories_are_under_project_root():
    settings = load_settings()

    assert settings.data_dir == settings.project_root / "data"
    assert settings.logs_dir == settings.project_root / "logs"
