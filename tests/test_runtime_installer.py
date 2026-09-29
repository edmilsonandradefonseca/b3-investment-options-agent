from pathlib import Path


def test_runtime_installer_preserves_local_b3_environment() -> None:
    script = Path("scripts/install_b3_runtime.sh").read_text(encoding="utf-8")

    assert 'EnvironmentFile=-$ENV_FILE' in script
    assert 'EnvironmentFile=-$RUNTIME_ROOT/b3.env' in script


def test_runtime_installer_does_not_embed_secret_values() -> None:
    script = Path("scripts/install_b3_runtime.sh").read_text(encoding="utf-8")

    assert "OPENAI_API_KEY=" not in script
    assert "OPLAB_API_TOKEN=" not in script
    assert "BRAPI_TOKEN=" not in script
