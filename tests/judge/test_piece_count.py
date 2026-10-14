import subprocess
import sys


def run_tally(*args, cwd):
    return subprocess.run(
        [sys.executable, "-m", "tally", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def write(tmp_path, content):
    path = tmp_path / "input.txt"
    path.write_bytes(content.encode("utf-8"))
    return path


def test_D1_counts_lines_words_characters(tmp_path):
    path = write(tmp_path, "one two\nthree\n")
    result = run_tally(str(path), cwd=tmp_path)
    assert result.stdout == f"2 3 14 {path}\n"
    assert result.returncode == 0


def test_D2_empty_file_prints_zeros(tmp_path):
    path = write(tmp_path, "")
    result = run_tally(str(path), cwd=tmp_path)
    assert result.stdout == f"0 0 0 {path}\n"


def test_D3_no_final_newline(tmp_path):
    path = write(tmp_path, "a b")
    result = run_tally(str(path), cwd=tmp_path)
    assert result.stdout == f"0 2 3 {path}\n"


def test_D4_characters_are_unicode_characters(tmp_path):
    path = write(tmp_path, "héllo wörld\n")
    result = run_tally(str(path), cwd=tmp_path)
    assert result.stdout == f"1 2 12 {path}\n"


def test_D5_missing_file_exits_2(tmp_path):
    missing = tmp_path / "missing.txt"
    result = run_tally(str(missing), cwd=tmp_path)
    assert result.returncode == 2
    assert result.stdout == ""
    assert "missing.txt" in result.stderr
