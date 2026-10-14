import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _pyproject():
    return (ROOT / "pyproject.toml").read_text()


def test_D1_test_extra_lists_pytest():
    text = _pyproject()
    assert re.search(r'name\s*=\s*["\']tally["\']', text)
    match = re.search(r"^test\s*=\s*\[(.*?)\]", text, re.S | re.M)
    assert match, "no test extra in pyproject.toml"
    assert "pytest" in match.group(1)


def test_D2_tally_is_importable():
    import tally

    assert tally.__name__ == "tally"


def test_D3_version_is_not_empty():
    import tally

    assert isinstance(tally.__version__, str)
    assert tally.__version__.strip()


def test_D4_own_smoke_test_passes():
    smoke = ROOT / "tests" / "test_smoke.py"
    assert smoke.is_file()
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(smoke), "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
