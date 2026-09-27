from pathlib import Path


def test_real_uc_acceptance_script_has_all_use_cases():
    text = Path("scripts/uc_real_acceptance.py").read_text(encoding="utf-8")
    for number in range(1, 13):
        assert f'"UC-{number:02d}"' in text
    assert '"LIMITED"' in text
    assert "B3 REAL UC01-UC12 ACCEPTANCE" in text
    assert "B3 REAL UC ACCEPTANCE COMPLETED" in text


def test_real_uc_acceptance_compiles():
    source = Path("scripts/uc_real_acceptance.py").read_text(encoding="utf-8")
    compile(source, "scripts/uc_real_acceptance.py", "exec")
