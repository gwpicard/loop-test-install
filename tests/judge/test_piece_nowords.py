# Intent: `tally --top N <file>` on a file with no words says so on stderr and exits 1, not silent success.
import subprocess
import sys


def run_tally(*args, cwd):
    return subprocess.run(
        [sys.executable, "-m", "tally", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def test_D1_empty_file_reports_no_words(tmp_path):
    (tmp_path / "empty.txt").write_bytes(b"")
    result = run_tally("--top", "2", "empty.txt", cwd=tmp_path)
    assert result.stderr == "tally: empty.txt: no words\n"
    assert result.stdout == ""
    assert result.returncode == 1


def test_D2_digits_and_punctuation_report_no_words(tmp_path):
    (tmp_path / "digits.txt").write_bytes(b"123 !!! 456\n")
    result = run_tally("--top", "2", "digits.txt", cwd=tmp_path)
    assert result.stderr == "tally: digits.txt: no words\n"
    assert result.stdout == ""
    assert result.returncode == 1


def test_D3_file_with_words_still_prints_top(tmp_path):
    (tmp_path / "words.txt").write_bytes(b"b a b c a b\n")
    result = run_tally("--top", "2", "words.txt", cwd=tmp_path)
    assert result.stdout == "b 3\na 2\n"
    assert result.returncode == 0


def test_D4_plain_count_on_empty_file_unchanged(tmp_path):
    (tmp_path / "empty.txt").write_bytes(b"")
    result = run_tally("empty.txt", cwd=tmp_path)
    assert result.stdout == "0 0 0 empty.txt\n"
    assert result.returncode == 0


def test_D5_missing_file_with_top_exits_2(tmp_path):
    result = run_tally("--top", "2", "missing.txt", cwd=tmp_path)
    assert result.stdout == ""
    assert result.returncode == 2
    assert result.stderr.startswith("tally: missing.txt: No such file")
    assert result.stderr.endswith(" or directory\n")
