import json

import pytest

from tally.cli import main
from tally.compare import count_words, run_compare, split_args

TEXT = """\
== words ==
word a.txt b.txt total files
the 2 1 3 2
cat 2 0 2 1
sat 1 1 2 2
dog 0 1 1 1

== per_file ==
file words unique exclusive
a.txt 5 3 1
b.txt 3 3 1

== totals ==
files 2
words 8
unique 4
shared 2
exclusive 2
shown 4
hidden 0
"""

CSV = """\
# words
word,a.txt,b.txt,total,files
the,2,1,3,2
cat,2,0,2,1
sat,1,1,2,2
dog,0,1,1,1

# per_file
file,words,unique,exclusive
a.txt,5,3,1
b.txt,3,3,1

# totals
name,value
files,2
words,8
unique,4
shared,2
exclusive,2
shown,4
hidden,0
"""

MARKDOWN = """\
## words

| word | a.txt | b.txt | total | files |
| --- | --- | --- | --- | --- |
| the | 2 | 1 | 3 | 2 |
| cat | 2 | 0 | 2 | 1 |
| sat | 1 | 1 | 2 | 2 |
| dog | 0 | 1 | 1 | 1 |

## per_file

| file | words | unique | exclusive |
| --- | --- | --- | --- |
| a.txt | 5 | 3 | 1 |
| b.txt | 3 | 3 | 1 |

## totals

| name | value |
| --- | --- |
| files | 2 |
| words | 8 |
| unique | 4 |
| shared | 2 |
| exclusive | 2 |
| shown | 4 |
| hidden | 0 |
"""

TOTALS = {
    "files": 2,
    "words": 8,
    "unique": 4,
    "shared": 2,
    "exclusive": 2,
    "shown": 4,
    "hidden": 0,
}

NEED_TWO = "tally: --compare needs at least two files\n"
BAD_MINIMUM = "tally: {} needs a whole number of at least 1\n"


@pytest.fixture
def ab(tmp_path, monkeypatch):
    (tmp_path / "a.txt").write_text("the cat the cat sat")
    (tmp_path / "b.txt").write_text("the dog sat")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def run(capsys, *args):
    code = main(["--compare", *args])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def words_of(capsys, *args):
    code, out, err = run(capsys, "a.txt", "b.txt", "--format", "json", *args)
    assert (code, err) == (0, "")
    return [row["word"] for row in json.loads(out)["words"]]


def test_text_default(ab, capsys):
    assert run(capsys, "a.txt", "b.txt") == (0, TEXT, "")


def test_text_format_by_name(ab, capsys):
    assert run(capsys, "a.txt", "b.txt", "--format", "text") == (0, TEXT, "")


def test_csv(ab, capsys):
    assert run(capsys, "a.txt", "b.txt", "--format", "csv") == (0, CSV, "")


def test_tsv(ab, capsys):
    expected = CSV.replace(",", "\t")
    assert run(capsys, "a.txt", "b.txt", "--format", "tsv") == (0, expected, "")


def test_markdown(ab, capsys):
    assert run(capsys, "a.txt", "b.txt", "--format", "markdown") == (0, MARKDOWN, "")


def test_json(ab, capsys):
    code, out, err = run(capsys, "a.txt", "b.txt", "--format", "json")
    assert (code, err) == (0, "")
    assert out.endswith("\n")
    data = json.loads(out)
    assert list(data) == ["files", "words", "per_file", "totals"]
    assert data["files"] == ["a.txt", "b.txt"]
    assert data["words"][1] == {
        "word": "cat",
        "counts": {"a.txt": 2, "b.txt": 0},
        "total": 2,
        "files": 1,
    }
    assert list(data["words"][0]) == ["word", "counts", "total", "files"]
    assert data["per_file"][0] == {"file": "a.txt", "words": 5, "unique": 3, "exclusive": 1}
    assert list(data["per_file"][0]) == ["file", "words", "unique", "exclusive"]
    assert data["totals"] == TOTALS
    assert list(data["totals"]) == list(TOTALS)


def test_csv_quotes_only_when_needed(tmp_path, monkeypatch, capsys):
    (tmp_path / "x,y.txt").write_text("a")
    (tmp_path / "b.txt").write_text("a")
    monkeypatch.chdir(tmp_path)
    _, out, _ = run(capsys, "x,y.txt", "b.txt", "--format", "csv")
    assert out.startswith('# words\nword,"x,y.txt",b.txt,total,files\na,1,1,2,2\n')


@pytest.mark.parametrize("section", ["words", "per_file", "totals"])
def test_one_section_text(ab, capsys, section):
    _, out, _ = run(capsys, "a.txt", "b.txt", "--section", section)
    blocks = {b.split("\n", 1)[0]: b for b in TEXT.rstrip("\n").split("\n\n")}
    assert out == blocks[f"== {section} =="] + "\n"


@pytest.mark.parametrize("section", ["words", "per_file", "totals"])
def test_one_section_json(ab, capsys, section):
    _, out, _ = run(capsys, "a.txt", "b.txt", "--format", "json", "--section", section)
    assert list(json.loads(out)) == ["files", section]


def test_section_all(ab, capsys):
    assert run(capsys, "--section", "all", "a.txt", "b.txt") == (0, TEXT, "")


@pytest.mark.parametrize(
    "order, expected",
    [
        ("total", ["the", "cat", "sat", "dog"]),
        ("alpha", ["cat", "dog", "sat", "the"]),
        ("files", ["sat", "the", "cat", "dog"]),
        ("spread", ["cat", "dog", "the", "sat"]),
    ],
)
def test_sorts(ab, capsys, order, expected):
    assert words_of(capsys, "--sort", order) == expected


def test_spread_uses_all_files(tmp_path, monkeypatch, capsys):
    (tmp_path / "a.txt").write_text("x x x x a")
    (tmp_path / "b.txt").write_text("x x x x b")
    (tmp_path / "c.txt").write_text("x x x x x x x x x")
    monkeypatch.chdir(tmp_path)
    _, out, _ = run(capsys, "a.txt", "b.txt", "c.txt", "--format", "json", "--sort", "spread")
    assert [r["word"] for r in json.loads(out)["words"]] == ["x", "a", "b"]


def test_min_total(ab, capsys):
    assert words_of(capsys, "--min-total", "2") == ["the", "cat", "sat"]
    assert words_of(capsys, "--min-total", "3") == ["the"]


def test_min_files(ab, capsys):
    assert words_of(capsys, "--min-files", "2") == ["the", "sat"]


def test_minimums_combine(ab, capsys):
    assert words_of(capsys, "--min-total", "3", "--min-files", "2") == ["the"]
    assert words_of(capsys, "--min-total", "2", "--min-files", "1") == ["the", "cat", "sat"]
    assert words_of(capsys, "--min-total", "1", "--min-files", "2") == ["the", "sat"]
    assert words_of(capsys, "--min-total", "1", "--min-files", "1") == ["the", "cat", "sat", "dog"]


def test_filter_changes_only_shown_and_hidden(ab, capsys):
    _, out, _ = run(capsys, "a.txt", "b.txt", "--format", "json", "--min-files", "2")
    data = json.loads(out)
    assert data["totals"] == dict(TOTALS, shown=2, hidden=2)
    assert data["per_file"][0]["unique"] == 3


def test_exclusive_across_three_files(tmp_path, monkeypatch, capsys):
    (tmp_path / "a.txt").write_text("p p q")
    (tmp_path / "b.txt").write_text("q r")
    (tmp_path / "c.txt").write_text("r s")
    monkeypatch.chdir(tmp_path)
    _, out, _ = run(capsys, "a.txt", "b.txt", "c.txt", "--format", "json")
    data = json.loads(out)
    assert [r["exclusive"] for r in data["per_file"]] == [1, 0, 1]
    assert data["totals"]["shared"] == 2
    assert data["totals"]["exclusive"] == 2


def test_word_rule(tmp_path, monkeypatch, capsys):
    (tmp_path / "a.txt").write_text("Don't stop, DON'T 42 'go'")
    (tmp_path / "b.txt").write_text("go")
    monkeypatch.chdir(tmp_path)
    assert words_of(capsys) == ["don't", "go", "stop"]
    assert count_words("Don't 'x' a-b") == {"don't": 1, "x": 1, "a": 1, "b": 1}


@pytest.mark.parametrize(
    "args, message",
    [
        (
            ["--format", "xml"],
            "tally: unknown --format value: xml (use text, json, csv, markdown, tsv)\n",
        ),
        (
            ["--section", "nope"],
            "tally: unknown --section value: nope (use words, per_file, totals, all)\n",
        ),
        (
            ["--sort", "count"],
            "tally: unknown --sort value: count (use total, alpha, files, spread)\n",
        ),
        (["--min-total", "0"], BAD_MINIMUM.format("--min-total")),
        (["--min-total", "x"], BAD_MINIMUM.format("--min-total")),
        (["--min-files", "-1"], BAD_MINIMUM.format("--min-files")),
        (["--min-files", "1.5"], BAD_MINIMUM.format("--min-files")),
        (["--min-files", "٣"], BAD_MINIMUM.format("--min-files")),
        (["--bogus"], "tally: unknown option: --bogus\n"),
        (["--top", "3"], "tally: unknown option: --top\n"),
        (["--format"], "tally: --format needs a value\n"),
    ],
)
def test_option_errors(ab, capsys, args, message):
    assert run(capsys, "a.txt", "b.txt", *args) == (2, "", message)


def test_file_count_errors(ab, capsys):
    assert run(capsys) == (2, "", NEED_TWO)
    assert run(capsys, "--format", "json") == (2, "", NEED_TWO)
    assert run(capsys, "a.txt") == (2, "", NEED_TWO)
    assert run(capsys, "a.txt", "b.txt", "a.txt") == (
        2,
        "",
        "tally: file named more than once: a.txt\n",
    )
    assert run(capsys, "a.txt", "a.txt", "b.txt", "b.txt")[2] == (
        "tally: file named more than once: a.txt, b.txt\n"
    )


def test_missing_file_still_compares_others(ab, capsys):
    code, out, err = run(capsys, "a.txt", "missing.txt", "b.txt")
    assert code == 2
    assert out == TEXT
    assert err == "tally: missing.txt: No such file or directory\n"


def test_bad_utf8_still_compares_others(ab, capsys):
    (ab / "bad.txt").write_bytes(b"\xff\xfe")
    code, out, err = run(capsys, "bad.txt", "a.txt", "b.txt")
    assert (code, out) == (2, TEXT)
    assert err == "tally: bad.txt: not valid UTF-8\n"


def test_fewer_than_two_readable_files(ab, capsys):
    code, out, err = run(capsys, "a.txt", "missing.txt")
    assert (code, out) == (2, "")
    assert "missing.txt" in err
    code, out, err = run(capsys, "one.txt", "two.txt")
    assert (code, out) == (2, "")
    assert "one.txt" in err and "two.txt" in err


def test_no_words(tmp_path, monkeypatch, capsys):
    (tmp_path / "a.txt").write_text("123 !!!")
    (tmp_path / "b.txt").write_text("")
    monkeypatch.chdir(tmp_path)
    assert run(capsys, "a.txt", "b.txt") == (1, "", "tally: no words\n")


def test_words_in_one_file_only(tmp_path, monkeypatch, capsys):
    (tmp_path / "a.txt").write_text("alpha beta")
    (tmp_path / "b.txt").write_text("")
    monkeypatch.chdir(tmp_path)
    _, out, _ = run(capsys, "a.txt", "b.txt", "--format", "json")
    data = json.loads(out)
    assert data["per_file"][0] == {"file": "a.txt", "words": 2, "unique": 2, "exclusive": 2}
    assert data["totals"]["shared"] == 0
    assert data["totals"]["exclusive"] == 2
    assert data["per_file"][1] == {"file": "b.txt", "words": 0, "unique": 0, "exclusive": 0}


def test_compare_only_first_argument(ab, capsys):
    assert main(["a.txt", "--compare"]) == 2
    assert capsys.readouterr().out == "0 5 19 a.txt\n0 5 19 total\n"


def test_run_compare_direct(ab, capsys):
    assert run_compare(["a.txt", "b.txt"]) == 0
    assert capsys.readouterr().out == TEXT


def test_split_args():
    assert split_args(["x", "--sort", "alpha", "y"])[1] == ["x", "y"]
    assert split_args(["--min-total", "5"])[0]["--min-total"] == "5"
    assert split_args(["--min-total", "5"])[0]["--format"] == "text"
