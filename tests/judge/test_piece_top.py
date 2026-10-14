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


def test_D1_most_frequent_first(tmp_path):
    path = write(tmp_path, "b a b c a b\n")
    result = run_tally("--top", "2", str(path), cwd=tmp_path)
    assert result.stdout == "b 3\na 2\n"
    assert result.returncode == 0


def test_D2_ties_are_alphabetical(tmp_path):
    path = write(tmp_path, "pear apple fig apple pear fig kiwi\n")
    result = run_tally("--top", "3", str(path), cwd=tmp_path)
    assert result.stdout == "apple 2\nfig 2\npear 2\n"


def test_D3_words_are_lowercase_letter_runs(tmp_path):
    path = write(tmp_path, "Hello, hello! HELLO-world 42 x2y\n")
    result = run_tally("--top", "2", str(path), cwd=tmp_path)
    assert result.stdout == "hello 3\nworld 1\n"


def test_D4_n_larger_than_distinct_words(tmp_path):
    path = write(tmp_path, "a b\n")
    result = run_tally("--top", "10", str(path), cwd=tmp_path)
    assert result.stdout == "a 1\nb 1\n"
    assert result.returncode == 0


def test_D5_no_words_prints_nothing(tmp_path):
    path = write(tmp_path, "123 !!! 456\n")
    result = run_tally("--top", "3", str(path), cwd=tmp_path)
    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""


def test_D6_invalid_n_exits_2(tmp_path):
    path = write(tmp_path, "a b\n")
    for bad in ("abc", "0"):
        result = run_tally("--top", bad, str(path), cwd=tmp_path)
        assert result.returncode == 2, bad
        assert "--top" in result.stderr, bad
        assert result.stdout == "", bad
