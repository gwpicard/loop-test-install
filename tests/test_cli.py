from tally.cli import main


def write_file(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text)
    return str(path)


def test_two_files_print_a_total(tmp_path, capsys):
    first = write_file(tmp_path, "a.txt", "one two\n")
    second = write_file(tmp_path, "b.txt", "three\n")
    assert main([first, second]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines == [f"1 2 8 {first}", f"1 1 6 {second}", "2 3 14 total"]


def test_missing_file_sets_exit_code_and_skips_total_share(tmp_path, capsys):
    first = write_file(tmp_path, "a.txt", "one two\n")
    missing = str(tmp_path / "missing.txt")
    assert main([first, missing]) == 2
    captured = capsys.readouterr()
    assert captured.out.splitlines() == [f"1 2 8 {first}", "1 2 8 total"]
    assert f"tally: {missing}: No such file or directory" in captured.err


def test_same_file_twice_counts_twice(tmp_path, capsys):
    first = write_file(tmp_path, "a.txt", "one\n")
    assert main([first, first]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == "2 2 8 total"


def test_one_file_has_no_total(tmp_path, capsys):
    first = write_file(tmp_path, "a.txt", "one\n")
    assert main([first]) == 0
    assert capsys.readouterr().out == f"1 1 4 {first}\n"


def test_no_file_prints_usage(capsys):
    assert main([]) == 2
    assert capsys.readouterr().err == "usage: tally <file>\n"


def test_top_lists_most_frequent_words(tmp_path, capsys):
    first = write_file(tmp_path, "a.txt", "b a b c\n")
    assert main(["--top", "2", first]) == 0
    assert capsys.readouterr().out == "b 2\na 1\n"


def test_top_on_file_without_words_reports_it(tmp_path, capsys):
    first = write_file(tmp_path, "a.txt", "123 !!! 456\n")
    assert main(["--top", "2", first]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == f"tally: {first}: no words\n"


def test_top_with_two_files_prints_usage(tmp_path, capsys):
    first = write_file(tmp_path, "a.txt", "a\n")
    assert main(["--top", "2", first, first]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "usage: tally --top N <file>\n"


def test_top_rejects_bad_number(tmp_path, capsys):
    first = write_file(tmp_path, "a.txt", "a\n")
    assert main(["--top", "0", first]) == 2
    assert "whole number" in capsys.readouterr().err


def test_top_with_missing_file_fails(tmp_path, capsys):
    assert main(["--top", "1", str(tmp_path / "none.txt")]) == 2
    assert "No such file" in capsys.readouterr().err
