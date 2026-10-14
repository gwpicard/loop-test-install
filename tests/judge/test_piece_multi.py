# Intent: let `tally` count several files in one run and print one line per file plus a final `total` line.
import subprocess
import sys

A_TEXT = "one two three\nfour five\n"  # 2 lines, 5 words, 24 chars
B_TEXT = "alpha\nbeta gamma delta\nepsilon zeta eta theta\n"  # 3 lines, 8 words, 46 chars
A_LINE = "2 5 24 a.txt\n"
B_LINE = "3 8 46 b.txt\n"


def run_tally(*args, cwd):
    return subprocess.run(
        [sys.executable, "-m", "tally", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def make_files(tmp_path):
    (tmp_path / "a.txt").write_bytes(A_TEXT.encode("utf-8"))
    (tmp_path / "b.txt").write_bytes(B_TEXT.encode("utf-8"))


def test_D1_two_files_print_lines_and_total(tmp_path):
    make_files(tmp_path)
    result = run_tally("a.txt", "b.txt", cwd=tmp_path)
    assert result.stdout == A_LINE + B_LINE + "5 13 70 total\n"
    assert result.returncode == 0


def test_D1_lines_follow_argument_order(tmp_path):
    make_files(tmp_path)
    result = run_tally("b.txt", "a.txt", cwd=tmp_path)
    assert result.stdout == B_LINE + A_LINE + "5 13 70 total\n"
    assert result.returncode == 0


def test_D2_missing_file_is_reported(tmp_path):
    make_files(tmp_path)
    result = run_tally("a.txt", "missing.txt", "b.txt", cwd=tmp_path)
    assert result.stderr.startswith("tally: missing.txt: No such file")
    assert result.stderr.endswith(" or directory\n")
    assert result.stderr.count("\n") == 1
    assert result.stdout == A_LINE + B_LINE + "5 13 70 total\n"
    assert result.returncode == 2


def test_D3_same_file_twice_counts_twice(tmp_path):
    make_files(tmp_path)
    result = run_tally("a.txt", "a.txt", cwd=tmp_path)
    assert result.stdout == A_LINE + A_LINE + "4 10 48 total\n"
    assert result.returncode == 0


def test_D4_one_file_has_no_total_line(tmp_path):
    make_files(tmp_path)
    result = run_tally("a.txt", cwd=tmp_path)
    assert result.stdout == A_LINE
    assert result.returncode == 0


def test_D5_top_with_one_file_still_works(tmp_path):
    (tmp_path / "a.txt").write_bytes(b"b a b c a b\n")
    result = run_tally("--top", "2", "a.txt", cwd=tmp_path)
    assert result.stdout == "b 3\na 2\n"
    assert result.returncode == 0


def test_D6_top_with_two_files_is_usage_error(tmp_path):
    make_files(tmp_path)
    result = run_tally("--top", "2", "a.txt", "b.txt", cwd=tmp_path)
    assert "usage: tally --top N <file>" in result.stderr
    assert result.stdout == ""
    assert result.returncode == 2
