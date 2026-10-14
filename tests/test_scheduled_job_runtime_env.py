from pathlib import Path


def _source(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_nightly_timer_loads_shared_and_b3_runtime_env_files():
    source = _source("scripts/install_nightly_intelligence_timer.sh")
    assert "/opt/joao-runtime/joao.env" in source
    assert "/etc/b3-runtime.env" in source
    assert "/opt/b3-runtime/b3.env" in source
    assert "EnvironmentFile=-${SHARED_ENV_FILE}" in source
    assert "EnvironmentFile=-${RUNTIME_ENV_FILE}" in source
    assert "EnvironmentFile=-${RUNTIME_ENV_FILE_2}" in source


def test_macro_timer_loads_shared_and_b3_runtime_env_files():
    source = _source("scripts/install_macro_refresh_timer.sh")
    assert "/opt/joao-runtime/joao.env" in source
    assert "/etc/b3-runtime.env" in source
    assert "/opt/b3-runtime/b3.env" in source
    assert "EnvironmentFile=-${SHARED_ENV_FILE}" in source
    assert "EnvironmentFile=-${RUNTIME_ENV_FILE}" in source
    assert "EnvironmentFile=-${RUNTIME_ENV_FILE_2}" in source


def test_scheduled_jobs_keep_canonical_project_root_and_do_not_manage_shared_services():
    for path in (
        "scripts/install_nightly_intelligence_timer.sh",
        "scripts/install_macro_refresh_timer.sh",
    ):
        source = _source(path)
        assert "Environment=B3_AGENT_PROJECT_ROOT=${REPO}" in source
        assert "systemctl restart ollama" not in source
        assert "systemctl stop ollama" not in source
        assert "systemctl restart joao" not in source
        assert "systemctl stop joao" not in source
