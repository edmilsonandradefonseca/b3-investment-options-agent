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
        "scripts/run_continuous_intelligence.sh",
        "scripts/install_continuous_intelligence_timers.sh",
        "scripts/run_v43_continuous_acceptance.sh",
        "scripts/deploy_v43_continuous_backend.sh",
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


def test_v43_continuous_acceptance_enforces_nonblocking_and_shared_lock():
    text = (ROOT / "scripts/validate_v43_continuous_runtime.py").read_text(
        encoding="utf-8"
    )
    assert '"deepseek_inline": False' in text
    assert "LOCAL_REASONING_LOCK_WAIT_SECONDS" in text
    assert "overlap_dedupe" in text
    assert "LocalRelevanceScreenJob" in text
    assert "CvmReconciliationJob" in text
    assert "/intelligence/local/status" in text


def test_v43_deploy_is_acceptance_first_and_verifies_production():
    text = (ROOT / "scripts/deploy_v43_continuous_backend.sh").read_text(
        encoding="utf-8"
    )
    assert text.index("run_v43_continuous_acceptance.sh") < text.index(
        "install_continuous_intelligence_timers.sh"
    )
    assert "BACKEND_CONTINUOUS_READY=PASS" in text
    assert "b3-continuous-intelligence.timer" in text
    assert "/intelligence/local/status" in text
    assert "restart joao-scheduler.service" in text


def test_v43_acceptance_treats_local_relevance_as_optional_derived_context():
    text = (ROOT / "scripts/validate_v43_continuous_runtime.py").read_text(
        encoding="utf-8"
    )
    assert '{"READY", "DEGRADED", "DEFERRED"}' in text
    assert "non-ready relevance output was incorrectly promoted" in text
    assert '"contained_nonblocking"' in text
