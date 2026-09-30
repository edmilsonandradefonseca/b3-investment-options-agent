from __future__ import annotations

from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def test_v43_shell_wrappers_are_syntax_valid():
    scripts = (
        "scripts/run_local_evidence_analyst.sh",
        "scripts/run_v43_async_acceptance.sh",
        "scripts/run_v43_full_acceptance.sh",
        "scripts/install_nightly_intelligence_timer.sh",
    )
    for relative in scripts:
        subprocess.run(
            ["bash", "-n", str(ROOT / relative)],
            check=True,
        )


def test_v43_worker_wrapper_uses_lower_cpu_priority():
    text = (ROOT / "scripts/run_local_evidence_analyst.sh").read_text(
        encoding="utf-8"
    )
    assert 'Nice=15' in text
    assert 'CPUWeight=10' in text


def test_v43_nightly_script_is_enqueue_only():
    text = (ROOT / "scripts/run_nightly_intelligence.py").read_text(
        encoding="utf-8"
    )
    assert 'local_analysis_mode="enqueue"' in text
