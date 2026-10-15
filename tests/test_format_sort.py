from tally.cli import main


def test_table_widens_for_long_words_and_big_counts(tmp_path, capsys):
    path = tmp_path / "in.txt"
    path.write_text("a " * 123456 + "longerword\n")
    assert main(["--top", "2", "--format", "table", str(path)]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "word         count"
    assert lines[1] == "----------  ------"
    assert lines[2] == "a" + " " * 11 + "123456"


def test_table_keeps_header_width_for_short_words(tmp_path, capsys):
    path = tmp_path / "in.txt"
    path.write_text("a b b\n")
    assert main(["--top", "2", "--format", "table", str(path)]) == 0
    assert capsys.readouterr().out == "word  count\n----  -----\nb         2\na         1\n"


def test_ties_are_ordered_by_word(tmp_path, capsys):
    path = tmp_path / "in.txt"
    path.write_text("b a\n")
    assert main(["--top", "2", str(path)]) == 0
    assert capsys.readouterr().out == "a 1\nb 1\n"


def test_main_reads_sys_argv_by_default(tmp_path, capsys, monkeypatch):
    path = tmp_path / "in.txt"
    path.write_text("b a b\n")
    monkeypatch.setattr("sys.argv", ["tally", "--top", "1", str(path)])
    assert main() == 0
    assert capsys.readouterr().out == "b 2\n"


def test_top_rejects_non_ascii_digits(tmp_path, capsys):
    path = tmp_path / "in.txt"
    path.write_text("a\n")
    assert main(["--top", "٣", str(path)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "tally: --top needs a whole number of at least 1\n"


def test_top_value_cannot_stand_in_for_the_top_option(tmp_path, capsys):
    path = tmp_path / "in.txt"
    path.write_text("a\n")
    assert main(["--format", "--top", str(path)]) == 2
    assert capsys.readouterr().err == "usage: tally --top N <file>\n"


def test_each_option_may_come_first(tmp_path, capsys):
    path = tmp_path / "in.txt"
    path.write_text("b a b\n")
    assert main(["--format", "csv", "--top", "1", str(path)]) == 0
    assert capsys.readouterr().out == "word,count\nb,2\n"
    assert main(["--sort", "alpha", "--top", "1", str(path)]) == 0
    assert capsys.readouterr().out == "b 2\n"


def test_options_without_top_are_not_top_mode(tmp_path, capsys):
    path = tmp_path / "in.txt"
    path.write_text("a\n")
    for name in ("--format", "--sort"):
        assert main([name, str(path)]) == 2
        out = capsys.readouterr().out
        assert out.endswith("1 1 2 total\n")


def test_unknown_option_name_prints_usage(tmp_path, capsys):
    path = tmp_path / "in.txt"
    path.write_text("a\n")
    assert main(["--top", "1", "--size", "x", str(path)]) == 2
    assert capsys.readouterr().err == "usage: tally --top N <file>\n"
