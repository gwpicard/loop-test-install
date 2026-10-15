from tally.cli import main


def test_table_widens_for_long_words_and_big_counts(tmp_path, capsys):
    path = tmp_path / "in.txt"
    path.write_text("a " * 123456 + "longerword\n")
    assert main(["--top", "2", "--format", "table", str(path)]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "word         count"
    assert lines[1] == "----------  ------"
    assert lines[2] == "a" + " " * 11 + "123456"


def test_unknown_option_name_prints_usage(tmp_path, capsys):
    path = tmp_path / "in.txt"
    path.write_text("a\n")
    assert main(["--top", "1", "--size", "x", str(path)]) == 2
    assert capsys.readouterr().err == "usage: tally --top N <file>\n"
