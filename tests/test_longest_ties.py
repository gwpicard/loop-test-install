from tally.cli import main


def test_equal_length_ties_use_the_word_not_the_count(tmp_path, capsys):
    path = tmp_path / "a.txt"
    path.write_text("aa aa bb")
    assert main(["--top", "2", "--longest-first", str(path)]) == 0
    assert capsys.readouterr().out.splitlines() == ["aa 2", "bb 1"]


def test_flags_with_summary_and_longest_first(tmp_path, capsys):
    path = tmp_path / "a.txt"
    path.write_text("aa aa bb")
    args = ["--top", "2", "--summary", "--longest-first", str(path)]
    assert main(args) == 0
    assert capsys.readouterr().out.splitlines()[-1] == (
        "summary: words=3 unique=2 shown=2 hidden=0"
    )


def test_option_without_value_prints_usage(capsys):
    assert main(["--top", "2", "--format"]) == 2
    assert capsys.readouterr().err == "usage: tally --top N <file>\n"
