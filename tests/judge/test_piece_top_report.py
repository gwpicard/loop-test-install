# Intent: `tally --top` can filter, order by length and summarise, and `tally --by-file` gives that report for each of several files.
import json

import pytest

FILES = {
    "a.txt": b"the cat and the cat and the dog saw a bird\n",
    "b.txt": b"dog dog cat\n",
    "c.txt": b"pear plum pear fig plum kiwi\n",
    "empty.txt": b"",
}
SUM_A = "summary: words=11 unique=7 shown=2 hidden=5"
SUM_B = "summary: words=3 unique=2 shown=2 hidden=0"
G_AB = "summary (all files): files=2 words=14 unique=7 shown=4 hidden=3"
G_ABC = "summary (all files): files=3 words=20 unique=11 shown=6 hidden=5"
G_ZERO = "summary (all files): files=0 words=0 unique=0 shown=0 hidden=0"
TOP_USAGE = "usage: tally --top N <file>\n"
FILE_USAGE = "usage: tally --by-file --top N <file>...\n"
TABLE_A2 = "word  count\n----  -----\nthe       3\nand       2\n"
TABLE_B2 = "word  count\n----  -----\ndog       2\ncat       1\n"


def run(tmp_path, capsys, monkeypatch, args):
    from tally.cli import main

    monkeypatch.chdir(tmp_path)
    for name, content in FILES.items():
        (tmp_path / name).write_bytes(content)
    capsys.readouterr()
    code = main(args)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


@pytest.fixture
def tally(tmp_path, capsys, monkeypatch):
    def call(*args):
        return run(tmp_path, capsys, monkeypatch, list(args))

    return call


def rows(*pairs):
    return [{"word": w, "count": c} for w, c in pairs]


# ---- D1: filters ----


def test_D1_min_count(tally):
    assert tally("--top", "5", "--min-count", "2", "a.txt") == (
        0,
        "the 3\nand 2\ncat 2\n",
        "",
    )


def test_D1_min_length(tally):
    assert tally("--top", "10", "--min-length", "3", "a.txt") == (
        0,
        "the 3\nand 2\ncat 2\nbird 1\ndog 1\nsaw 1\n",
        "",
    )


def test_D1_both_filters_together(tally):
    args = ("--top", "10", "--min-length", "2", "--min-count", "2", "a.txt")
    assert tally(*args) == (0, "the 3\nand 2\ncat 2\n", "")


def test_D1_filters_on_c_txt(tally):
    assert tally("--top", "5", "--min-count", "2", "c.txt") == (
        0,
        "pear 2\nplum 2\n",
        "",
    )
    assert tally("--top", "5", "--min-length", "4", "c.txt") == (
        0,
        "pear 2\nplum 2\nkiwi 1\n",
        "",
    )


def test_D1_filter_runs_before_top_n(tally):
    assert tally("--top", "4", "--min-length", "3", "a.txt") == (
        0,
        "the 3\nand 2\ncat 2\nbird 1\n",
        "",
    )


# ---- D2: tie rule ----


def test_D2_ties_pick_fig_over_kiwi(tally):
    # A filter first, so this test fails today on an assertion.
    assert tally("--top", "3", "--min-length", "4", "c.txt")[1] == "pear 2\nplum 2\nkiwi 1\n"
    assert tally("--top", "3", "c.txt") == (0, "pear 2\nplum 2\nfig 1\n", "")


def test_D2_sort_alpha_on_c(tally):
    # A filter first, so this test fails today on an assertion.
    args = ("--top", "3", "--min-length", "4", "--sort", "alpha", "c.txt")
    assert tally(*args)[1] == "kiwi 1\npear 2\nplum 2\n"
    assert tally("--top", "3", "--sort", "alpha", "c.txt") == (
        0,
        "fig 1\npear 2\nplum 2\n",
        "",
    )


def test_D2_longest_first_top3_on_c(tally):
    assert tally("--top", "3", "--longest-first", "c.txt") == (
        0,
        "pear 2\nplum 2\nfig 1\n",
        "",
    )


def test_D2_longest_first_top4_on_c(tally):
    expected = (0, "kiwi 1\npear 2\nplum 2\nfig 1\n", "")
    assert tally("--top", "4", "--longest-first", "c.txt") == expected
    assert tally("--top", "4", "--sort", "alpha", "--longest-first", "c.txt") == expected


def test_D2_longest_first_on_a(tally):
    assert tally("--top", "4", "--longest-first", "a.txt") == (
        0,
        "and 2\ncat 2\nthe 3\na 1\n",
        "",
    )


def test_D2_longest_first_with_min_length(tally):
    args = ("--top", "4", "--min-length", "2", "--longest-first", "a.txt")
    assert tally(*args) == (0, "bird 1\nand 2\ncat 2\nthe 3\n", "")


def test_D2_longest_first_with_summary(tally):
    args = ("--top", "2", "--min-length", "2", "--longest-first", "--summary", "a.txt")
    assert tally(*args) == (0, f"and 2\nthe 3\n{SUM_A}\n", "")


# ---- D3: summary of one file ----


def test_D3_summary_plain(tally):
    assert tally("--top", "2", "--summary", "a.txt") == (
        0,
        f"the 3\nand 2\n{SUM_A}\n",
        "",
    )


def test_D3_summary_table(tally):
    args = ("--top", "2", "--format", "table", "--summary", "a.txt")
    assert tally(*args) == (0, f"{TABLE_A2}\n{SUM_A}\n", "")


def test_D3_summary_csv(tally):
    args = ("--top", "2", "--format", "csv", "--summary", "a.txt")
    assert tally(*args) == (0, f"word,count\nthe,3\nand,2\n# {SUM_A}\n", "")


def test_D3_summary_json(tally):
    args = ("--top", "2", "--format", "json", "--summary", "a.txt")
    code, out, err = tally(*args)
    assert out.endswith("\n") and out.count("\n") == 1
    assert json.loads(out) == {
        "rows": rows(("the", 3), ("and", 2)),
        "summary": {"words": 11, "unique": 7, "shown": 2, "hidden": 5},
    }
    assert (code, err) == (0, "")


def test_D3_json_without_summary_is_the_plain_list(tally):
    code, out, err = tally("--top", "2", "--format", "json", "a.txt")
    assert json.loads(out) == rows(("the", 3), ("and", 2))
    assert (code, err) == (0, "")
    # The summary form must differ, so this test fails while --summary is unknown.
    code, out, err = tally("--top", "2", "--format", "json", "--summary", "a.txt")
    assert out.startswith('{"rows"')
    assert json.loads(out)["rows"] == rows(("the", 3), ("and", 2))


def test_D3_filter_does_not_change_words_or_unique(tally):
    args = ("--top", "10", "--min-length", "3", "--summary", "a.txt")
    assert tally(*args) == (
        0,
        "the 3\nand 2\ncat 2\nbird 1\ndog 1\nsaw 1\n"
        "summary: words=11 unique=7 shown=6 hidden=1\n",
        "",
    )


# ---- D4: errors of --top ----


@pytest.mark.parametrize("option", ["--min-count", "--min-length"])
@pytest.mark.parametrize("bad", ["0", "abc", "-1", "1.5"])
def test_D4_bad_filter_value(tally, option, bad):
    code, out, err = tally("--top", "2", option, bad, "a.txt")
    assert err == f"tally: {option} needs a whole number of at least 1\n"
    assert out == ""
    assert code == 2


@pytest.mark.parametrize("bad", ["size", "length"])
def test_D4_unknown_sort_value(tally, bad):
    # A valid run with a new option first, so this test fails today on an assertion.
    assert tally("--top", "2", "--min-count", "2", "a.txt") == (
        0,
        "the 3\nand 2\n",
        "",
    )
    code, out, err = tally("--top", "2", "--sort", bad, "a.txt")
    assert err == f"tally: unknown --sort value: {bad} (use count or alpha)\n"
    assert out == ""
    assert code == 2


@pytest.mark.parametrize(
    "args",
    [
        ("--top", "2", "--min-count"),
        ("--top", "2", "--summary", "--min-length"),
        ("--top", "2", "--bogus", "1"),
        ("--top", "2", "--longest-first", "--bogus"),
    ],
)
def test_D4_missing_value_or_unknown_option_prints_usage(tally, args):
    # A valid run with the new flags first, so this test fails today.
    assert tally("--top", "2", "--longest-first", "a.txt")[0] == 0
    code, out, err = tally(*args, "a.txt")
    assert err == TOP_USAGE
    assert out == ""
    assert code == 2


def test_D4_flags_are_accepted_before_usage_errors(tally):
    code, out, err = tally("--top", "2", "--longest-first", "--summary", "a.txt")
    assert out == f"and 2\nthe 3\n{SUM_A}\n"
    assert (code, err) == (0, "")


def test_D4_filters_remove_every_word(tally):
    assert tally("--top", "3", "--min-length", "20", "a.txt") == (
        1,
        "",
        "tally: a.txt: no words match\n",
    )


def test_D4_filters_remove_every_word_with_summary(tally):
    args = ("--top", "3", "--min-length", "20", "--summary", "a.txt")
    assert tally(*args) == (1, "", "tally: a.txt: no words match\n")


# ---- D5: --by-file layout ----


def test_D5_by_file_plain(tally):
    args = ("--by-file", "--top", "2", "--summary", "a.txt", "b.txt")
    assert tally(*args) == (
        0,
        f"==> a.txt <==\nthe 3\nand 2\n{SUM_A}\n\n"
        f"==> b.txt <==\ndog 2\ncat 1\n{SUM_B}\n\n{G_AB}\n",
        "",
    )


def test_D5_by_file_table(tally):
    args = ("--by-file", "--top", "2", "--format", "table", "--summary", "a.txt", "b.txt")
    assert tally(*args) == (
        0,
        f"==> a.txt <==\n{TABLE_A2}\n{SUM_A}\n\n"
        f"==> b.txt <==\n{TABLE_B2}\n{SUM_B}\n\n{G_AB}\n",
        "",
    )


def test_D5_by_file_csv(tally):
    args = ("--by-file", "--top", "2", "--format", "csv", "--summary", "a.txt", "b.txt")
    assert tally(*args) == (
        0,
        f"==> a.txt <==\nword,count\nthe,3\nand,2\n# {SUM_A}\n\n"
        f"==> b.txt <==\nword,count\ndog,2\ncat,1\n# {SUM_B}\n\n# {G_AB}\n",
        "",
    )


def test_D5_by_file_json(tally):
    args = ("--by-file", "--top", "2", "--format", "json", "--summary", "a.txt", "b.txt")
    code, out, err = tally(*args)
    assert out.endswith("\n") and out.count("\n") == 1
    assert json.loads(out) == {
        "files": [
            {
                "file": "a.txt",
                "rows": rows(("the", 3), ("and", 2)),
                "summary": {"words": 11, "unique": 7, "shown": 2, "hidden": 5},
            },
            {
                "file": "b.txt",
                "rows": rows(("dog", 2), ("cat", 1)),
                "summary": {"words": 3, "unique": 2, "shown": 2, "hidden": 0},
            },
        ],
        "summary": {"files": 2, "words": 14, "unique": 7, "shown": 4, "hidden": 3},
    }
    assert (code, err) == (0, "")


def test_D5_without_summary_plain_table_csv(tally):
    assert tally("--by-file", "--top", "2", "a.txt", "b.txt") == (
        0,
        "==> a.txt <==\nthe 3\nand 2\n\n==> b.txt <==\ndog 2\ncat 1\n",
        "",
    )
    args = ("--by-file", "--top", "2", "--format", "table", "a.txt", "b.txt")
    assert tally(*args) == (
        0,
        f"==> a.txt <==\n{TABLE_A2}\n==> b.txt <==\n{TABLE_B2}",
        "",
    )
    args = ("--by-file", "--top", "2", "--format", "csv", "a.txt", "b.txt")
    assert tally(*args) == (
        0,
        "==> a.txt <==\nword,count\nthe,3\nand,2\n\n"
        "==> b.txt <==\nword,count\ndog,2\ncat,1\n",
        "",
    )


def test_D5_without_summary_json(tally):
    args = ("--by-file", "--top", "2", "--format", "json", "a.txt", "b.txt")
    code, out, err = tally(*args)
    assert out.endswith("\n") and out.count("\n") == 1
    assert json.loads(out) == {
        "files": [
            {"file": "a.txt", "rows": rows(("the", 3), ("and", 2))},
            {"file": "b.txt", "rows": rows(("dog", 2), ("cat", 1))},
        ]
    }
    assert (code, err) == (0, "")


# ---- D6: global summary ----


def test_D6_global_summary_plain(tally):
    code, out, err = tally("--by-file", "--top", "2", "--summary", "a.txt", "b.txt")
    assert out.endswith(f"\n\n{G_AB}\n")
    assert (code, err) == (0, "")


def test_D6_global_summary_csv(tally):
    args = ("--by-file", "--top", "2", "--format", "csv", "--summary", "a.txt", "b.txt")
    assert tally(*args)[1].endswith(f"\n\n# {G_AB}\n")


def test_D6_global_summary_json(tally):
    args = ("--by-file", "--top", "2", "--format", "json", "--summary", "a.txt", "b.txt")
    out = tally(*args)[1]
    assert out.startswith('{"files"')
    data = json.loads(out)
    assert data["summary"] == {
        "files": 2,
        "words": 14,
        "unique": 7,
        "shown": 4,
        "hidden": 3,
    }


def test_D6_global_summary_three_files(tally):
    args = ("--by-file", "--top", "2", "--summary", "a.txt", "b.txt", "c.txt")
    code, out, err = tally(*args)
    assert out == (
        f"==> a.txt <==\nthe 3\nand 2\n{SUM_A}\n\n"
        f"==> b.txt <==\ndog 2\ncat 1\n{SUM_B}\n\n"
        "==> c.txt <==\npear 2\nplum 2\n"
        "summary: words=6 unique=4 shown=2 hidden=2\n\n"
        f"{G_ABC}\n"
    )
    assert (code, err) == (0, "")


def test_D6_global_summary_table(tally):
    args = ("--by-file", "--top", "2", "--format", "table", "--summary", "a.txt", "b.txt")
    assert tally(*args)[1].endswith(f"{SUM_B}\n\n{G_AB}\n")


def test_D6_filtered_out_file_is_still_counted(tally):
    args = ("--by-file", "--top", "5", "--min-length", "4", "--summary", "a.txt", "b.txt")
    assert tally(*args) == (
        1,
        "==> a.txt <==\nbird 1\n"
        "summary: words=11 unique=7 shown=1 hidden=6\n\n"
        "summary (all files): files=2 words=14 unique=7 shown=1 hidden=6\n",
        "tally: b.txt: no words match\n",
    )


def test_D6_all_files_filtered_out_json(tally):
    args = (
        "--by-file", "--top", "5", "--min-length", "20", "--format", "json",
        "--summary", "a.txt", "b.txt",
    )
    code, out, err = tally(*args)
    assert out.startswith('{"files"')
    assert json.loads(out) == {
        "files": [],
        "summary": {"files": 2, "words": 14, "unique": 7, "shown": 0, "hidden": 7},
    }
    assert code == 1
    assert err == "tally: a.txt: no words match\ntally: b.txt: no words match\n"


def test_D6_missing_file_is_not_counted(tally):
    args = ("--by-file", "--top", "2", "--summary", "a.txt", "missing.txt")
    code, out, err = tally(*args)
    assert out == (
        f"==> a.txt <==\nthe 3\nand 2\n{SUM_A}\n\n"
        "summary (all files): files=1 words=11 unique=7 shown=2 hidden=5\n"
    )
    assert err.startswith("tally: missing.txt:")
    assert code == 2


def test_D6_empty_file_is_not_counted(tally):
    args = ("--by-file", "--top", "2", "--summary", "a.txt", "empty.txt")
    assert tally(*args) == (
        1,
        f"==> a.txt <==\nthe 3\nand 2\n{SUM_A}\n\n"
        "summary (all files): files=1 words=11 unique=7 shown=2 hidden=5\n",
        "tally: empty.txt: no words\n",
    )


def test_D6_no_file_counted_plain(tally):
    code, out, err = tally("--by-file", "--top", "2", "--summary", "missing.txt")
    assert G_ZERO in out.splitlines()
    assert out.strip() == G_ZERO
    assert err.startswith("tally: missing.txt:")
    assert code == 2


def test_D6_no_file_counted_json(tally):
    args = ("--by-file", "--top", "2", "--format", "json", "--summary", "empty.txt")
    code, out, err = tally(*args)
    assert out.startswith('{"files"')
    assert json.loads(out) == {
        "files": [],
        "summary": {"files": 0, "words": 0, "unique": 0, "shown": 0, "hidden": 0},
    }
    assert err == "tally: empty.txt: no words\n"
    assert code == 1


def test_D6_no_global_summary_without_flag(tally):
    code, out, _ = tally("--by-file", "--top", "2", "a.txt")
    assert out == "==> a.txt <==\nthe 3\nand 2\n"
    assert code == 0


# ---- D7: --by-file behaviour ----


def test_D7_min_count(tally):
    args = ("--by-file", "--top", "5", "--min-count", "2", "a.txt", "b.txt")
    assert tally(*args) == (
        0,
        "==> a.txt <==\nthe 3\nand 2\ncat 2\n\n==> b.txt <==\ndog 2\n",
        "",
    )


def test_D7_min_length_skips_file_without_match(tally):
    args = ("--by-file", "--top", "5", "--min-length", "4", "a.txt", "b.txt")
    assert tally(*args) == (
        1,
        "==> a.txt <==\nbird 1\n",
        "tally: b.txt: no words match\n",
    )


def test_D7_longest_first(tally):
    args = (
        "--by-file", "--top", "4", "--min-length", "2", "--longest-first",
        "a.txt", "b.txt",
    )
    assert tally(*args) == (
        0,
        "==> a.txt <==\nbird 1\nand 2\ncat 2\nthe 3\n\n==> b.txt <==\ncat 1\ndog 2\n",
        "",
    )


def test_D7_tie_rule_in_the_same_run(tally):
    args = ("--by-file", "--top", "3", "a.txt", "c.txt")
    assert tally(*args) == (
        0,
        "==> a.txt <==\nthe 3\nand 2\ncat 2\n\n==> c.txt <==\npear 2\nplum 2\nfig 1\n",
        "",
    )


def test_D7_missing_file_is_named_and_others_print(tally):
    args = ("--by-file", "--top", "1", "a.txt", "missing.txt", "b.txt")
    code, out, err = tally(*args)
    assert out == "==> a.txt <==\nthe 3\n\n==> b.txt <==\ndog 2\n"
    assert err.startswith("tally: missing.txt:")
    assert code == 2


def test_D7_file_with_no_words(tally):
    args = ("--by-file", "--top", "1", "a.txt", "empty.txt")
    assert tally(*args) == (
        1,
        "==> a.txt <==\nthe 3\n",
        "tally: empty.txt: no words\n",
    )


def test_D7_missing_file_wins_over_no_words(tally):
    code, out, err = tally("--by-file", "--top", "1", "empty.txt", "missing.txt")
    assert out == ""
    assert err.startswith("tally: empty.txt: no words\ntally: missing.txt:")
    assert code == 2


def test_D7_json_with_no_rows(tally):
    args = ("--by-file", "--top", "5", "--min-length", "20", "--format", "json", "a.txt")
    assert tally(*args) == (1, '{"files": []}\n', "tally: a.txt: no words match\n")


@pytest.mark.parametrize(
    "args",
    [
        ("--top", "2"),
        ("a.txt",),
        ("--top", "2", "--bogus", "a.txt"),
        ("--top", "2", "--min-count"),
    ],
)
def test_D7_usage_errors(tally, args):
    # A valid run first, so this test fails today on an assertion.
    assert tally("--by-file", "--top", "1", "a.txt")[1] == "==> a.txt <==\nthe 3\n"
    code, out, err = tally("--by-file", *args)
    assert err == FILE_USAGE
    assert out == ""
    assert code == 2


def test_D7_bad_option_values(tally):
    code, out, err = tally("--by-file", "--top", "2", "--min-count", "0", "a.txt")
    assert err == "tally: --min-count needs a whole number of at least 1\n"
    assert (code, out) == (2, "")
    code, out, err = tally("--by-file", "--top", "2", "--min-length", "x", "a.txt")
    assert err == "tally: --min-length needs a whole number of at least 1\n"
    assert (code, out) == (2, "")
    code, out, err = tally("--by-file", "--top", "2", "--sort", "length", "a.txt")
    assert err == "tally: unknown --sort value: length (use count or alpha)\n"
    assert (code, out) == (2, "")


# ---- D8: unchanged behaviour ----


def test_D8_plain_file_unchanged(tally):
    assert tally("a.txt") == (0, "1 11 43 a.txt\n", "")


def test_D8_two_files_unchanged(tally):
    assert tally("a.txt", "b.txt") == (
        0,
        "1 11 43 a.txt\n1 3 12 b.txt\n2 14 55 total\n",
        "",
    )


def test_D8_top_unchanged(tally):
    assert tally("--top", "2", "a.txt") == (0, "the 3\nand 2\n", "")


def test_D8_top_csv_alpha_unchanged(tally):
    assert tally("--top", "3", "--format", "csv", "--sort", "alpha", "a.txt") == (
        0,
        "word,count\nand,2\ncat,2\nthe,3\n",
        "",
    )


def test_D8_top_with_two_files_prints_usage(tally):
    assert tally("--top", "2", "a.txt", "a.txt") == (2, "", TOP_USAGE)


def test_D8_top_empty_file_unchanged(tally):
    assert tally("--top", "2", "empty.txt") == (1, "", "tally: empty.txt: no words\n")
