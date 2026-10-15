# Intent: `tally --top` can filter words by count and length, sort rows by length, and add a one-line summary of the file.
import json

TEXT = b"the cat and the cat and the dog saw a bird\n"


def run(tmp_path, capsys, args, content=TEXT):
    from tally.cli import main

    path = tmp_path / "a.txt"
    path.write_bytes(content)
    capsys.readouterr()
    code = main([*args, str(path)])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_D1_filters_before_the_top_cut(tmp_path, capsys):
    code, out, err = run(tmp_path, capsys, ["--top", "5", "--min-count", "2"])
    assert out == "the 3\nand 2\ncat 2\n"
    assert err == ""
    assert code == 0


def test_D1_min_length_keeps_words_of_three_or_more(tmp_path, capsys):
    code, out, err = run(tmp_path, capsys, ["--top", "10", "--min-length", "3"])
    assert out == "the 3\nand 2\ncat 2\nbird 1\ndog 1\nsaw 1\n"
    assert err == ""
    assert code == 0


def test_D1_both_filters_must_hold(tmp_path, capsys):
    args = ["--top", "10", "--min-length", "2", "--min-count", "2"]
    code, out, err = run(tmp_path, capsys, args)
    assert out == "the 3\nand 2\ncat 2\n"
    assert err == ""
    assert code == 0


def test_D1_filter_applies_before_top_n(tmp_path, capsys):
    code, out, err = run(tmp_path, capsys, ["--top", "4", "--min-length", "3"])
    assert out == "the 3\nand 2\ncat 2\nbird 1\n"
    assert code == 0


def test_D1_inner_apostrophe_counts_as_a_character(tmp_path, capsys):
    code, out, err = run(
        tmp_path, capsys, ["--top", "5", "--min-length", "3"], b"it's an ox\n"
    )
    assert out == "it's 1\n"
    assert err == ""
    assert code == 0


def test_D2_sort_length_orders_chosen_rows(tmp_path, capsys):
    code, out, err = run(tmp_path, capsys, ["--top", "4", "--sort", "length"])
    assert out == "and 2\ncat 2\nthe 3\na 1\n"
    assert err == ""
    assert code == 0


def test_D2_sort_length_longest_first_with_filter(tmp_path, capsys):
    args = ["--top", "4", "--min-length", "2", "--sort", "length"]
    code, out, err = run(tmp_path, capsys, args)
    assert out == "bird 1\nand 2\ncat 2\nthe 3\n"
    assert err == ""
    assert code == 0


def test_D3_summary_plain(tmp_path, capsys):
    code, out, err = run(tmp_path, capsys, ["--top", "2", "--summary"])
    assert out == "the 3\nand 2\nsummary: words=11 unique=7 shown=2 hidden=5\n"
    assert err == ""
    assert code == 0


def test_D3_summary_table(tmp_path, capsys):
    args = ["--top", "2", "--format", "table", "--summary"]
    code, out, err = run(tmp_path, capsys, args)
    assert out == (
        "word  count\n"
        "----  -----\n"
        "the       3\n"
        "and       2\n"
        "\n"
        "summary: words=11 unique=7 shown=2 hidden=5\n"
    )
    assert err == ""
    assert code == 0


def test_D3_summary_csv(tmp_path, capsys):
    args = ["--top", "2", "--format", "csv", "--summary"]
    code, out, err = run(tmp_path, capsys, args)
    assert out == (
        "word,count\n"
        "the,3\n"
        "and,2\n"
        "# summary: words=11 unique=7 shown=2 hidden=5\n"
    )
    assert err == ""
    assert code == 0


def test_D3_summary_json(tmp_path, capsys):
    args = ["--top", "2", "--format", "json", "--summary"]
    code, out, err = run(tmp_path, capsys, args)
    assert out.count("\n") == 1
    assert json.loads(out) == {
        "rows": [{"word": "the", "count": 3}, {"word": "and", "count": 2}],
        "summary": {"words": 11, "unique": 7, "shown": 2, "hidden": 5},
    }
    assert err == ""
    assert code == 0


def test_D3_json_without_summary_is_unchanged(tmp_path, capsys):
    code, out, err = run(tmp_path, capsys, ["--top", "2", "--format", "json"])
    assert json.loads(out) == [
        {"word": "the", "count": 3},
        {"word": "and", "count": 2},
    ]
    code2, out2, _ = run(
        tmp_path, capsys, ["--top", "2", "--format", "json", "--summary"]
    )
    assert json.loads(out2)["rows"] == json.loads(out)
    assert code == 0


def test_D3_filter_does_not_change_words_or_unique(tmp_path, capsys):
    args = ["--top", "10", "--min-length", "3", "--summary"]
    code, out, err = run(tmp_path, capsys, args)
    assert out == (
        "the 3\nand 2\ncat 2\nbird 1\ndog 1\nsaw 1\n"
        "summary: words=11 unique=7 shown=6 hidden=1\n"
    )
    assert err == ""
    assert code == 0


def test_D4_bad_min_count_value(tmp_path, capsys):
    for bad in ["0", "abc", "-1", "1.5"]:
        code, out, err = run(tmp_path, capsys, ["--top", "2", "--min-count", bad])
        assert err == "tally: --min-count needs a whole number of at least 1\n"
        assert out == ""
        assert code == 2


def test_D4_bad_min_length_value(tmp_path, capsys):
    for bad in ["0", "abc", "-1", "1.5"]:
        code, out, err = run(tmp_path, capsys, ["--top", "2", "--min-length", bad])
        assert err == "tally: --min-length needs a whole number of at least 1\n"
        assert out == ""
        assert code == 2


def test_D4_unknown_sort_value(tmp_path, capsys):
    code, out, err = run(tmp_path, capsys, ["--top", "2", "--sort", "size"])
    assert err == "tally: unknown --sort value: size (use count, alpha or length)\n"
    assert out == ""
    assert code == 2


def test_D4_missing_value_or_unknown_option_prints_usage(tmp_path, capsys):
    # The new flag is accepted, so a valid run succeeds first.
    code, out, _ = run(tmp_path, capsys, ["--top", "2", "--summary"])
    assert code == 0
    assert out.endswith("summary: words=11 unique=7 shown=2 hidden=5\n")
    for args in (
        ["--top", "2", "--min-count"],
        ["--top", "2", "--summary", "--min-length"],
        ["--top", "2", "--bogus", "1"],
        ["--top", "2", "--summary", "--bogus"],
    ):
        code, out, err = run(tmp_path, capsys, args)
        assert err.startswith("usage:")
        assert out == ""
        assert code == 2


def test_D5_filters_remove_every_word(tmp_path, capsys):
    code, out, err = run(tmp_path, capsys, ["--top", "3", "--min-length", "20"])
    assert out == ""
    assert err == f"tally: {tmp_path / 'a.txt'}: no words match\n"
    assert code == 1


def test_D5_no_words_match_with_summary(tmp_path, capsys):
    args = ["--top", "3", "--min-count", "9", "--summary"]
    code, out, err = run(tmp_path, capsys, args)
    assert out == ""
    assert err == f"tally: {tmp_path / 'a.txt'}: no words match\n"
    assert code == 1


def test_D6_plain_counts_unchanged(tmp_path, capsys):
    from tally.cli import main

    path = tmp_path / "a.txt"
    path.write_bytes(TEXT)
    capsys.readouterr()
    code = main([str(path)])
    captured = capsys.readouterr()
    assert captured.out == f"1 11 43 {path}\n"
    assert captured.err == ""
    assert code == 0


def test_D6_top_unchanged(tmp_path, capsys):
    code, out, err = run(tmp_path, capsys, ["--top", "2"])
    assert out == "the 3\nand 2\n"
    assert err == ""
    assert code == 0


def test_D6_csv_alpha_unchanged(tmp_path, capsys):
    args = ["--top", "3", "--format", "csv", "--sort", "alpha"]
    code, out, err = run(tmp_path, capsys, args)
    assert out == "word,count\nand,2\ncat,2\nthe,3\n"
    assert err == ""
    assert code == 0


def test_D6_empty_file_unchanged(tmp_path, capsys):
    code, out, err = run(tmp_path, capsys, ["--top", "2"], b"")
    assert out == ""
    assert err == f"tally: {tmp_path / 'a.txt'}: no words\n"
    assert code == 1
