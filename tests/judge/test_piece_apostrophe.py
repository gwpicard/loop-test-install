# Intent: `tally --top` counts a word with an apostrophe, such as "don't", as one word.


def run_top(tmp_path, capsys, content, top="2"):
    from tally.cli import main

    (tmp_path / "in.txt").write_bytes(content)
    capsys.readouterr()
    code = main(["--top", top, str(tmp_path / "in.txt")])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_D1_apostrophe_word_counts_as_one_word(tmp_path, capsys):
    code, out, err = run_top(tmp_path, capsys, b"don't don't stop\n")
    assert out == "don't 2\nstop 1\n"
    assert err == ""
    assert code == 0


def test_D2_apostrophe_word_count_ignores_case(tmp_path, capsys):
    code, out, err = run_top(tmp_path, capsys, b"Don't DON'T\n", top="1")
    assert out == "don't 2\n"
    assert err == ""
    assert code == 0


def test_D3_edge_apostrophes_are_not_part_of_the_word(tmp_path, capsys):
    code, out, err = run_top(tmp_path, capsys, b"'hello'\n", top="1")
    assert out == "hello 1\n"
    assert err == ""
    assert code == 0
    # An inner apostrophe stays, while the outer ones go.
    code, out, err = run_top(tmp_path, capsys, b"'don't'\n", top="1")
    assert out == "don't 1\n"
    assert err == ""
    assert code == 0


def test_D4_words_sort_by_count_then_name(tmp_path, capsys):
    code, out, err = run_top(tmp_path, capsys, b"b a b\n")
    assert out == "b 2\na 1\n"
    assert err == ""
    assert code == 0


def test_D5_file_with_no_words_reports_on_stderr(tmp_path, capsys):
    code, out, err = run_top(tmp_path, capsys, b"''' 123\n")
    assert err == f"tally: {tmp_path / 'in.txt'}: no words\n"
    assert out == ""
    assert code == 1
