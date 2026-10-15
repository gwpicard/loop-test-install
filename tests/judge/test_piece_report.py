# Intent: `tally --report FILE...` prints a word report in text, JSON, CSV or Markdown, with sort, min-count and summary.
import json


def run(capsys, *args):
    from tally.cli import main

    capsys.readouterr()
    code = main(list(args))
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def two_files(tmp_path):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("the cat the", encoding="utf-8")
    b.write_text("the dog", encoding="utf-8")
    return str(a), str(b)


SUMMARY_TEXT = "files: 2\nwords: 5\nunique: 3\nshown: 3\nhidden: 0\n"
SUMMARY = {"files": 2, "words": 5, "unique": 3, "shown": 3, "hidden": 0}


def test_D1_text_rows_and_summary(tmp_path, capsys):
    a, b = two_files(tmp_path)
    code, out, err = run(capsys, "--report", a, b)
    assert out == (
        "word count files\nthe 3 2\ncat 1 1\ndog 1 1\n\n" + SUMMARY_TEXT
    )
    assert err == ""
    assert code == 0


def test_D1_word_rule_matches_top(tmp_path, capsys):
    a = tmp_path / "a.txt"
    a.write_text("Don't DON'T 'hi' x2y\n", encoding="utf-8")
    code, out, err = run(capsys, "--report", str(a), "--no-summary")
    assert out == "word count files\ndon't 2 1\nhi 1 1\nx 1 1\ny 1 1\n"
    assert code == 0


def test_D2_json_format(tmp_path, capsys):
    a, b = two_files(tmp_path)
    code, out, err = run(capsys, "--report", "--format", "json", a, b)
    assert json.loads(out) == {
        "rows": [
            {"word": "the", "count": 3, "files": 2},
            {"word": "cat", "count": 1, "files": 1},
            {"word": "dog", "count": 1, "files": 1},
        ],
        "summary": SUMMARY,
    }
    assert code == 0


def test_D2_csv_format_has_no_summary(tmp_path, capsys):
    a, b = two_files(tmp_path)
    code, out, err = run(capsys, "--report", "--format", "csv", a, b)
    assert out == "word,count,files\nthe,3,2\ncat,1,1\ndog,1,1\n"
    assert code == 0


def test_D2_markdown_format(tmp_path, capsys):
    a, b = two_files(tmp_path)
    code, out, err = run(capsys, "--report", "--format", "markdown", a, b)
    lines = out.splitlines()
    assert lines[0] == "| word | count | files |"
    assert set(lines[1]) <= set("|- :") and "---" in lines[1]
    assert lines[2:5] == ["| the | 3 | 2 |", "| cat | 1 | 1 |", "| dog | 1 | 1 |"]
    assert "## Summary" in lines
    tail = lines[lines.index("## Summary") + 1 :]
    assert [x for x in tail if x] == [
        "- files: 2",
        "- words: 5",
        "- unique: 3",
        "- shown: 3",
        "- hidden: 0",
    ]
    assert code == 0


def test_D2_no_summary_in_every_format(tmp_path, capsys):
    a, b = two_files(tmp_path)
    code, out, err = run(capsys, "--report", "--no-summary", a, b)
    assert out == "word count files\nthe 3 2\ncat 1 1\ndog 1 1\n"
    code, out, err = run(
        capsys, "--report", "--format", "json", "--no-summary", a, b
    )
    data = json.loads(out)
    assert "summary" not in data
    assert len(data["rows"]) == 3
    code, out, err = run(
        capsys, "--report", "--format", "markdown", "--no-summary", a, b
    )
    assert "Summary" not in out
    assert out.splitlines()[2] == "| the | 3 | 2 |"
    assert code == 0


def test_D2_unknown_format_exits_2(tmp_path, capsys):
    a, b = two_files(tmp_path)
    code, out, err = run(capsys, "--report", "--format", "xml", a, b)
    assert code == 2
    assert out == ""
    assert "tally: unknown --format value: xml" in err


def test_D3_sort_alpha(tmp_path, capsys):
    a, b = two_files(tmp_path)
    code, out, err = run(
        capsys, "--report", "--sort", "alpha", "--no-summary", a, b
    )
    assert out == "word count files\ncat 1 1\ndog 1 1\nthe 3 2\n"
    assert code == 0


def test_D3_sort_files_high_to_low_ties_alphabetical(tmp_path, capsys):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("zed zed zed zed apple pear", encoding="utf-8")
    b.write_text("pear mango", encoding="utf-8")
    code, out, err = run(
        capsys, "--report", "--sort", "files", "--no-summary", str(a), str(b)
    )
    assert out == (
        "word count files\npear 2 2\napple 1 1\nmango 1 1\nzed 4 1\n"
    )
    assert code == 0


def test_D3_unknown_sort_exits_2(tmp_path, capsys):
    a, b = two_files(tmp_path)
    code, out, err = run(capsys, "--report", "--sort", "random", a, b)
    assert code == 2
    assert out == ""
    assert "random" in err


def test_D4_min_count_filters_and_counts_hidden(tmp_path, capsys):
    a, b = two_files(tmp_path)
    code, out, err = run(capsys, "--report", "--min-count", "2", a, b)
    assert out == (
        "word count files\nthe 3 2\n\n"
        "files: 2\nwords: 5\nunique: 3\nshown: 1\nhidden: 2\n"
    )
    assert code == 0


def test_D4_min_count_runs_before_sort(tmp_path, capsys):
    a = tmp_path / "a.txt"
    a.write_text("b b b a c c", encoding="utf-8")
    code, out, err = run(
        capsys,
        "--report",
        "--min-count",
        "2",
        "--sort",
        "alpha",
        "--no-summary",
        str(a),
    )
    assert out == "word count files\nb 3 1\nc 2 1\n"


def test_D4_bad_min_count_exits_2(tmp_path, capsys):
    a, b = two_files(tmp_path)
    for bad in ("0", "-1", "x", "1.5", ""):
        code, out, err = run(capsys, "--report", "--min-count", bad, a, b)
        assert code == 2, bad
        assert out == "", bad
        assert err != "", bad


def test_D5_missing_file_still_reports_others(tmp_path, capsys):
    a, _ = two_files(tmp_path)
    missing = str(tmp_path / "nope.txt")
    code, out, err = run(capsys, "--report", "--no-summary", a, missing)
    assert code == 2
    assert out == "word count files\nthe 2 1\ncat 1 1\n"
    assert missing in err


def test_D5_invalid_utf8_file_is_named(tmp_path, capsys):
    a, _ = two_files(tmp_path)
    bad = tmp_path / "bad.txt"
    bad.write_bytes(b"\xff\xfe\xfa")
    code, out, err = run(capsys, "--report", "--no-summary", a, str(bad))
    assert code == 2
    assert out == "word count files\nthe 2 1\ncat 1 1\n"
    assert str(bad) in err


def test_D5_no_words_exits_1(tmp_path, capsys):
    a = tmp_path / "a.txt"
    a.write_text("123 !!!\n", encoding="utf-8")
    code, out, err = run(capsys, "--report", str(a))
    assert code == 1
    assert out == ""
    assert "tally: no words" in err


def test_D5_no_file_prints_usage_and_exits_2(capsys):
    code, out, err = run(capsys, "--report")
    assert code == 2
    assert out == ""
    assert "usage" in err.lower()


def test_D6_single_and_multi_file_unchanged(tmp_path, capsys):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("one two\n", encoding="utf-8")
    b.write_text("three\n", encoding="utf-8")
    code, out, err = run(capsys, str(a))
    assert (code, out, err) == (0, f"1 2 8 {a}\n", "")
    code, out, err = run(capsys, str(a), str(b))
    assert (code, out, err) == (
        0,
        f"1 2 8 {a}\n1 1 6 {b}\n2 3 14 total\n",
        "",
    )


def test_D6_top_unchanged(tmp_path, capsys):
    a = tmp_path / "a.txt"
    a.write_text("one two\n", encoding="utf-8")
    code, out, err = run(capsys, "--top", "3", "--format", "csv", str(a))
    assert (code, out, err) == (0, "word,count\none,1\ntwo,1\n", "")


def test_D6_file_named_report_still_counted(tmp_path, capsys, monkeypatch):
    (tmp_path / "report").write_text("one two\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    code, out, err = run(capsys, "report")
    assert (code, out, err) == (0, "1 2 8 report\n", "")


def test_D6_top_with_report_rejected(tmp_path, capsys):
    a = tmp_path / "a.txt"
    a.write_text("one two\n", encoding="utf-8")
    for args in (
        ("--top", "2", "--report", str(a)),
        ("--report", "--top", "2", str(a)),
    ):
        code, out, err = run(capsys, *args)
        assert code == 2
        assert out == ""
        assert "--top" in err and "--report" in err
