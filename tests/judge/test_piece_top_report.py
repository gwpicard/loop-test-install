# Intent: `tally --top` can filter, order by length and summarise, and `tally --by-file` gives that report for each of several files.
import json

TEXT = b"the cat and the cat and the dog saw a bird\n"
OTHER = b"dog dog cat\n"
SUMMARY_A = "summary: words=11 unique=7 shown=2 hidden=5"
SUMMARY_B = "summary: words=3 unique=2 shown=2 hidden=0"
TOP_USAGE = "usage: tally --top N <file>\n"
FILE_USAGE = "usage: tally --by-file --top N <file>...\n"


def run(tmp_path, capsys, args, content=TEXT):
    from tally.cli import main

    path = tmp_path / "a.txt"
    path.write_bytes(content)
    capsys.readouterr()
    code = main([*args, str(path)])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def run_files(tmp_path, capsys, monkeypatch, args, extra=None):
    from tally.cli import main

    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.txt").write_bytes(TEXT)
    (tmp_path / "b.txt").write_bytes(OTHER)
    for name, content in (extra or {}).items():
        (tmp_path / name).write_bytes(content)
    capsys.readouterr()
    code = main(args)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def by_file(tmp_path, capsys, monkeypatch, options, files=("a.txt", "b.txt"), extra=None):
    args = ["--by-file", *options, *files]
    return run_files(tmp_path, capsys, monkeypatch, args, extra)


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
    assert err == ""
    assert code == 0


def test_D1_inner_apostrophe_counts_as_a_character(tmp_path, capsys):
    args = ["--top", "5", "--min-length", "3"]
    code, out, err = run(tmp_path, capsys, args, b"it's an ox\n")
    assert out == "it's 1\n"
    assert err == ""
    assert code == 0


def test_D2_longest_first_orders_chosen_rows(tmp_path, capsys):
    code, out, err = run(tmp_path, capsys, ["--top", "4", "--longest-first"])
    assert out == "and 2\ncat 2\nthe 3\na 1\n"
    assert err == ""
    assert code == 0


def test_D2_longest_first_with_filter(tmp_path, capsys):
    args = ["--top", "4", "--min-length", "2", "--longest-first"]
    code, out, err = run(tmp_path, capsys, args)
    assert out == "bird 1\nand 2\ncat 2\nthe 3\n"
    assert err == ""
    assert code == 0


def test_D2_longest_first_runs_after_sort_alpha(tmp_path, capsys):
    args = ["--top", "4", "--min-length", "2", "--sort", "alpha", "--longest-first"]
    code, out, err = run(tmp_path, capsys, args)
    assert out == "bird 1\nand 2\ncat 2\nthe 3\n"
    assert err == ""
    assert code == 0


def test_D2_longest_first_with_alpha_and_short_word(tmp_path, capsys):
    args = ["--top", "4", "--sort", "alpha", "--longest-first"]
    code, out, err = run(tmp_path, capsys, args)
    assert out == "and 2\ncat 2\nthe 3\na 1\n"
    assert err == ""
    assert code == 0


def test_D3_summary_plain(tmp_path, capsys):
    code, out, err = run(tmp_path, capsys, ["--top", "2", "--summary"])
    assert out == f"the 3\nand 2\n{SUMMARY_A}\n"
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
        f"{SUMMARY_A}\n"
    )
    assert err == ""
    assert code == 0


def test_D3_summary_csv(tmp_path, capsys):
    args = ["--top", "2", "--format", "csv", "--summary"]
    code, out, err = run(tmp_path, capsys, args)
    assert out == f"word,count\nthe,3\nand,2\n# {SUMMARY_A}\n"
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
    args = ["--top", "2", "--format", "json", "--summary"]
    code2, out2, _ = run(tmp_path, capsys, args)
    assert out2.startswith('{"rows"')
    assert json.loads(out2)["rows"] == json.loads(out)
    assert code == 0
    assert code2 == 0


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


def test_D4_sort_length_and_size_are_unknown_values(tmp_path, capsys):
    # A valid new option comes first, so this test fails today on an assertion.
    code, out, _ = run(tmp_path, capsys, ["--top", "2", "--min-count", "2"])
    assert out == "the 3\nand 2\n"
    assert code == 0
    for bad in ("size", "length"):
        args = ["--top", "2", "--min-count", "2", "--sort", bad]
        code, out, err = run(tmp_path, capsys, args)
        assert err == f"tally: unknown --sort value: {bad} (use count or alpha)\n"
        assert out == ""
        assert code == 2


def test_D4_missing_value_or_unknown_option_prints_usage(tmp_path, capsys):
    # A valid run with the new options comes first, so this test fails today.
    args = ["--top", "2", "--min-length", "2", "--longest-first", "--summary"]
    code, out, _ = run(tmp_path, capsys, args)
    assert out == f"the 3\nand 2\n{SUMMARY_A}\n"
    assert code == 0
    for args in (
        ["--top", "2", "--min-count"],
        ["--top", "2", "--summary", "--min-length"],
        ["--top", "2", "--bogus", "1"],
        ["--top", "2", "--longest-first", "--bogus"],
    ):
        code, out, err = run(tmp_path, capsys, args)
        assert err == TOP_USAGE
        assert out == ""
        assert code == 2


def test_D4_filters_remove_every_word(tmp_path, capsys):
    code, out, err = run(tmp_path, capsys, ["--top", "3", "--min-length", "20"])
    assert out == ""
    assert err == f"tally: {tmp_path / 'a.txt'}: no words match\n"
    assert code == 1


def test_D4_no_words_match_with_summary(tmp_path, capsys):
    args = ["--top", "3", "--min-count", "9", "--summary"]
    code, out, err = run(tmp_path, capsys, args)
    assert out == ""
    assert err == f"tally: {tmp_path / 'a.txt'}: no words match\n"
    assert code == 1


def test_D5_by_file_plain_summary(tmp_path, capsys, monkeypatch):
    code, out, err = by_file(tmp_path, capsys, monkeypatch, ["--top", "2", "--summary"])
    assert out == (
        "==> a.txt <==\n"
        "the 3\n"
        "and 2\n"
        f"{SUMMARY_A}\n"
        "\n"
        "==> b.txt <==\n"
        "dog 2\n"
        "cat 1\n"
        f"{SUMMARY_B}\n"
    )
    assert err == ""
    assert code == 0


def test_D5_by_file_table_summary(tmp_path, capsys, monkeypatch):
    options = ["--top", "2", "--format", "table", "--summary"]
    code, out, err = by_file(tmp_path, capsys, monkeypatch, options)
    assert out == (
        "==> a.txt <==\n"
        "word  count\n"
        "----  -----\n"
        "the       3\n"
        "and       2\n"
        "\n"
        f"{SUMMARY_A}\n"
        "\n"
        "==> b.txt <==\n"
        "word  count\n"
        "----  -----\n"
        "dog       2\n"
        "cat       1\n"
        "\n"
        f"{SUMMARY_B}\n"
    )
    assert err == ""
    assert code == 0


def test_D5_by_file_csv_summary(tmp_path, capsys, monkeypatch):
    options = ["--top", "2", "--format", "csv", "--summary"]
    code, out, err = by_file(tmp_path, capsys, monkeypatch, options)
    assert out == (
        "==> a.txt <==\n"
        "word,count\n"
        "the,3\n"
        "and,2\n"
        f"# {SUMMARY_A}\n"
        "\n"
        "==> b.txt <==\n"
        "word,count\n"
        "dog,2\n"
        "cat,1\n"
        f"# {SUMMARY_B}\n"
    )
    assert err == ""
    assert code == 0


def test_D5_by_file_json_summary(tmp_path, capsys, monkeypatch):
    options = ["--top", "2", "--format", "json", "--summary"]
    code, out, err = by_file(tmp_path, capsys, monkeypatch, options)
    assert out.startswith('{"files"')
    assert json.loads(out) == {
        "files": [
            {
                "file": "a.txt",
                "rows": [{"word": "the", "count": 3}, {"word": "and", "count": 2}],
                "summary": {"words": 11, "unique": 7, "shown": 2, "hidden": 5},
            },
            {
                "file": "b.txt",
                "rows": [{"word": "dog", "count": 2}, {"word": "cat", "count": 1}],
                "summary": {"words": 3, "unique": 2, "shown": 2, "hidden": 0},
            },
        ]
    }
    assert err == ""
    assert code == 0


def test_D5_by_file_without_summary_in_every_format(tmp_path, capsys, monkeypatch):
    code, out, err = by_file(tmp_path, capsys, monkeypatch, ["--top", "2"])
    assert out == "==> a.txt <==\nthe 3\nand 2\n\n==> b.txt <==\ndog 2\ncat 1\n"
    assert code == 0
    options = ["--top", "2", "--format", "table"]
    code, out, _ = by_file(tmp_path, capsys, monkeypatch, options)
    assert out == (
        "==> a.txt <==\n"
        "word  count\n"
        "----  -----\n"
        "the       3\n"
        "and       2\n"
        "\n"
        "==> b.txt <==\n"
        "word  count\n"
        "----  -----\n"
        "dog       2\n"
        "cat       1\n"
    )
    assert code == 0
    options = ["--top", "2", "--format", "csv"]
    code, out, _ = by_file(tmp_path, capsys, monkeypatch, options)
    assert out == (
        "==> a.txt <==\nword,count\nthe,3\nand,2\n\n"
        "==> b.txt <==\nword,count\ndog,2\ncat,1\n"
    )
    assert code == 0
    options = ["--top", "2", "--format", "json"]
    code, out, _ = by_file(tmp_path, capsys, monkeypatch, options)
    assert out.startswith('{"files"')
    assert json.loads(out) == {
        "files": [
            {
                "file": "a.txt",
                "rows": [{"word": "the", "count": 3}, {"word": "and", "count": 2}],
            },
            {
                "file": "b.txt",
                "rows": [{"word": "dog", "count": 2}, {"word": "cat", "count": 1}],
            },
        ]
    }
    assert code == 0


def test_D6_by_file_min_count(tmp_path, capsys, monkeypatch):
    options = ["--top", "5", "--min-count", "2"]
    code, out, err = by_file(tmp_path, capsys, monkeypatch, options)
    assert out == (
        "==> a.txt <==\nthe 3\nand 2\ncat 2\n\n==> b.txt <==\ndog 2\n"
    )
    assert err == ""
    assert code == 0


def test_D6_by_file_skips_file_with_no_match(tmp_path, capsys, monkeypatch):
    options = ["--top", "5", "--min-length", "4"]
    code, out, err = by_file(tmp_path, capsys, monkeypatch, options)
    assert out == "==> a.txt <==\nbird 1\n"
    assert err == "tally: b.txt: no words match\n"
    assert code == 1


def test_D6_by_file_json_with_no_rows_is_empty_list(tmp_path, capsys, monkeypatch):
    options = ["--top", "5", "--min-length", "20", "--format", "json"]
    code, out, err = by_file(tmp_path, capsys, monkeypatch, options)
    assert out == '{"files": []}\n'
    assert json.loads(out) == {"files": []}
    assert err == "tally: a.txt: no words match\ntally: b.txt: no words match\n"
    assert code == 1


def test_D6_by_file_longest_first(tmp_path, capsys, monkeypatch):
    options = ["--top", "4", "--min-length", "2", "--longest-first"]
    code, out, err = by_file(tmp_path, capsys, monkeypatch, options)
    assert out == (
        "==> a.txt <==\n"
        "bird 1\nand 2\ncat 2\nthe 3\n"
        "\n"
        "==> b.txt <==\n"
        "cat 1\ndog 2\n"
    )
    assert err == ""
    assert code == 0


def test_D6_by_file_missing_file_is_named_and_others_print(
    tmp_path, capsys, monkeypatch
):
    code, out, err = by_file(
        tmp_path,
        capsys,
        monkeypatch,
        ["--top", "1"],
        files=("a.txt", "missing.txt", "b.txt"),
    )
    assert out == "==> a.txt <==\nthe 3\n\n==> b.txt <==\ndog 2\n"
    assert err == "tally: missing.txt: No such file or directory\n"
    assert code == 2


def test_D6_by_file_file_with_no_words(tmp_path, capsys, monkeypatch):
    code, out, err = by_file(
        tmp_path,
        capsys,
        monkeypatch,
        ["--top", "1"],
        files=("a.txt", "empty.txt"),
        extra={"empty.txt": b""},
    )
    assert out == "==> a.txt <==\nthe 3\n"
    assert err == "tally: empty.txt: no words\n"
    assert code == 1


def test_D6_by_file_read_error_wins_over_no_words(tmp_path, capsys, monkeypatch):
    code, out, err = by_file(
        tmp_path,
        capsys,
        monkeypatch,
        ["--top", "1"],
        files=("empty.txt", "missing.txt"),
        extra={"empty.txt": b""},
    )
    assert out == ""
    assert err == (
        "tally: empty.txt: no words\n"
        "tally: missing.txt: No such file or directory\n"
    )
    assert code == 2


def test_D6_by_file_usage_and_option_errors(tmp_path, capsys, monkeypatch):
    # A valid run comes first, so this test fails today on an assertion.
    code, out, _ = by_file(tmp_path, capsys, monkeypatch, ["--top", "1"])
    assert out == "==> a.txt <==\nthe 3\n\n==> b.txt <==\ndog 2\n"
    assert code == 0
    for options, files in (
        (["--top", "2"], ()),
        ([], ("a.txt",)),
        (["--top", "2", "--bogus"], ("a.txt",)),
        (["--top", "2", "--min-count"], ("a.txt",)),
    ):
        code, out, err = by_file(tmp_path, capsys, monkeypatch, options, files)
        assert err == FILE_USAGE
        assert out == ""
        assert code == 2


def test_D6_by_file_bad_option_values(tmp_path, capsys, monkeypatch):
    code, out, err = by_file(
        tmp_path, capsys, monkeypatch, ["--top", "2", "--min-count", "0"]
    )
    assert err == "tally: --min-count needs a whole number of at least 1\n"
    assert out == ""
    assert code == 2
    code, out, err = by_file(
        tmp_path, capsys, monkeypatch, ["--top", "2", "--sort", "length"]
    )
    assert err == "tally: unknown --sort value: length (use count or alpha)\n"
    assert out == ""
    assert code == 2


def test_D7_plain_counts_unchanged(tmp_path, capsys, monkeypatch):
    code, out, err = run_files(tmp_path, capsys, monkeypatch, ["a.txt"])
    assert out == "1 11 43 a.txt\n"
    assert err == ""
    assert code == 0


def test_D7_two_files_unchanged(tmp_path, capsys, monkeypatch):
    code, out, err = run_files(tmp_path, capsys, monkeypatch, ["a.txt", "b.txt"])
    assert out == "1 11 43 a.txt\n1 3 12 b.txt\n2 14 55 total\n"
    assert err == ""
    assert code == 0


def test_D7_top_unchanged(tmp_path, capsys):
    code, out, err = run(tmp_path, capsys, ["--top", "2"])
    assert out == "the 3\nand 2\n"
    assert err == ""
    assert code == 0


def test_D7_csv_alpha_unchanged(tmp_path, capsys):
    args = ["--top", "3", "--format", "csv", "--sort", "alpha"]
    code, out, err = run(tmp_path, capsys, args)
    assert out == "word,count\nand,2\ncat,2\nthe,3\n"
    assert err == ""
    assert code == 0


def test_D7_top_with_two_files_prints_usage(tmp_path, capsys, monkeypatch):
    code, out, err = run_files(
        tmp_path, capsys, monkeypatch, ["--top", "2", "a.txt", "a.txt"]
    )
    assert out == ""
    assert err == TOP_USAGE
    assert code == 2


def test_D7_empty_file_unchanged(tmp_path, capsys):
    code, out, err = run(tmp_path, capsys, ["--top", "2"], b"")
    assert out == ""
    assert err == f"tally: {tmp_path / 'a.txt'}: no words\n"
    assert code == 1
