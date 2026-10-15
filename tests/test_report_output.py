from tally.cli import main


def test_markdown_summary_layout(tmp_path, capsys):
    path = tmp_path / "a.txt"
    path.write_text("the cat the")
    assert main(["--report", "--format", "markdown", str(path)]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "| word | count | files |",
        "| --- | --- | --- |",
        "| the | 2 | 1 |",
        "| cat | 1 | 1 |",
        "",
        "## Summary",
        "",
        "- files: 1",
        "- words: 3",
        "- unique: 2",
        "- shown: 2",
        "- hidden: 0",
    ]


def test_no_words_message(tmp_path, capsys):
    path = tmp_path / "a.txt"
    path.write_text("123")
    assert main(["--report", str(path)]) == 1
    assert capsys.readouterr().err == "tally: no words\n"


def write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text)
    return str(path)


def test_value_option_after_file(tmp_path, capsys):
    path = write(tmp_path, "a.txt", "b a a")
    assert main(["--report", path, "--format", "csv"]) == 0
    assert capsys.readouterr().out.splitlines()[1] == "a,2,1"


def test_value_option_without_value(tmp_path, capsys):
    path = write(tmp_path, "a.txt", "a")
    assert main(["--report", path, "--sort"]) == 2
    assert capsys.readouterr().err.startswith("usage: tally --report")


def test_min_count_message(tmp_path, capsys):
    path = write(tmp_path, "a.txt", "a")
    assert main(["--report", "--min-count", "0", path]) == 2
    err = capsys.readouterr().err
    assert err == "tally: --min-count needs a whole number of at least 1\n"


def test_top_message(capsys):
    assert main(["--report", "--top", "3", "a.txt"]) == 2
    assert capsys.readouterr().err == "tally: --top cannot be used with --report\n"


def test_top_first_then_report_message(capsys):
    assert main(["--top", "3", "--report", "a.txt"]) == 2
    assert capsys.readouterr().err == "tally: --top cannot be used with --report\n"


def test_missing_file_first_keeps_others(tmp_path, capsys):
    path = write(tmp_path, "a.txt", "a")
    assert main(["--report", str(tmp_path / "none.txt"), path]) == 2
    assert "a 1 1" in capsys.readouterr().out
