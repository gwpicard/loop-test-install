# Intent: tally --compare FILE FILE... compares word counts across two or more files, in five formats, with sort, minimum and section options.
import csv
import json
import re
import subprocess
import sys

import pytest


def run_tally(*args, cwd):
    return subprocess.run(
        [sys.executable, "-m", "tally", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def put(tmp_path, name, content):
    data = content if isinstance(content, bytes) else content.encode("utf-8")
    (tmp_path / name).write_bytes(data)


@pytest.fixture
def ab(tmp_path):
    put(tmp_path, "a.txt", "the cat the cat sat")
    put(tmp_path, "b.txt", "the dog sat")
    return tmp_path


def compare(tmp_path, *args):
    return run_tally("--compare", *args, cwd=tmp_path)


def norm(text):
    return text.replace("\r\n", "\n").rstrip("\n")


# ---- expected values for D1 (literals) ----

D1_WORDS = [
    ["word", "a.txt", "b.txt", "total", "files"],
    ["the", "2", "1", "3", "2"],
    ["cat", "2", "0", "2", "1"],
    ["sat", "1", "1", "2", "2"],
    ["dog", "0", "1", "1", "1"],
]
D1_PER_FILE = [
    ["file", "words", "unique", "exclusive"],
    ["a.txt", "5", "3", "1"],
    ["b.txt", "3", "3", "1"],
]
D1_TOTALS = [
    ["files", "2"],
    ["words", "8"],
    ["unique", "4"],
    ["shared", "2"],
    ["exclusive", "2"],
    ["shown", "4"],
    ["hidden", "0"],
]

D1_TEXT = """\
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
hidden 0"""

D1_CSV = """\
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
hidden,0"""

D1_TSV = D1_CSV.replace(",", "\t")

D1_JSON = {
    "files": ["a.txt", "b.txt"],
    "words": [
        {"word": "the", "counts": {"a.txt": 2, "b.txt": 1}, "total": 3, "files": 2},
        {"word": "cat", "counts": {"a.txt": 2, "b.txt": 0}, "total": 2, "files": 1},
        {"word": "sat", "counts": {"a.txt": 1, "b.txt": 1}, "total": 2, "files": 2},
        {"word": "dog", "counts": {"a.txt": 0, "b.txt": 1}, "total": 1, "files": 1},
    ],
    "per_file": [
        {"file": "a.txt", "words": 5, "unique": 3, "exclusive": 1},
        {"file": "b.txt", "words": 3, "unique": 3, "exclusive": 1},
    ],
    "totals": {
        "files": 2,
        "words": 8,
        "unique": 4,
        "shared": 2,
        "exclusive": 2,
        "shown": 4,
        "hidden": 0,
    },
}

HEADING = {
    "text": re.compile(r"^== (\w+) ==$"),
    "csv": re.compile(r"^# (\w+)$"),
    "tsv": re.compile(r"^# (\w+)$"),
    "markdown": re.compile(r"^## (\w+)$"),
}


def split_row(fmt, line):
    if fmt == "text":
        return line.split(" ")
    if fmt == "tsv":
        return line.split("\t")
    if fmt == "csv":
        return next(csv.reader([line]))
    cells = line.strip()
    assert cells.startswith("|") and cells.endswith("|"), line
    return [cell.strip() for cell in cells[1:-1].split("|")]


def parse_sections(fmt, out):
    """Return an ordered dict: section name -> list of rows."""
    sections = {}
    current = None
    for line in norm(out).split("\n"):
        if not line.strip():
            continue
        match = HEADING[fmt].match(line)
        if match:
            current = match.group(1)
            assert current not in sections
            sections[current] = []
        else:
            assert current is not None, f"row before heading: {line!r}"
            sections[current].append(split_row(fmt, line))
    if fmt == "markdown":
        for name, rows in sections.items():
            assert len(rows) >= 2
            assert all(re.fullmatch(r":?-+:?", cell) for cell in rows[1]), rows[1]
            del rows[1]
    return sections


def expected_sections(fmt):
    totals = [list(row) for row in D1_TOTALS]
    if fmt != "text":
        totals = [["name", "value"]] + totals
    return {"words": D1_WORDS, "per_file": D1_PER_FILE, "totals": totals}


def word_order(result):
    return [row["word"] for row in json.loads(result.stdout)["words"]]


# ---------------- D1 ----------------


def test_D1_text_all_sections(ab):
    result = compare(ab, "a.txt", "b.txt")
    assert result.returncode == 0
    assert norm(result.stdout) == D1_TEXT
    assert result.stderr == ""


def test_D1_options_may_come_before_or_after_files(ab):
    before = compare(ab, "--sort", "alpha", "--format", "csv", "a.txt", "b.txt")
    after = compare(ab, "a.txt", "b.txt", "--sort", "alpha", "--format", "csv")
    assert before.returncode == 0
    assert after.returncode == 0
    assert before.stdout == after.stdout
    assert parse_sections("csv", before.stdout)["words"][1][0] == "cat"


def test_D1_columns_follow_argument_order(ab):
    result = compare(ab, "b.txt", "a.txt", "--format", "json")
    data = json.loads(result.stdout)
    assert data["files"] == ["b.txt", "a.txt"]
    assert [row["file"] for row in data["per_file"]] == ["b.txt", "a.txt"]
    the = data["words"][0]
    assert the["word"] == "the"
    assert list(the["counts"].items()) == [("b.txt", 1), ("a.txt", 2)]


def test_D1_word_rule_lowercase_apostrophe_letters_only(tmp_path):
    put(tmp_path, "a.txt", "Don't stop, don't 42 go!")
    put(tmp_path, "b.txt", "'quoted' GO")
    result = compare(tmp_path, "a.txt", "b.txt", "--format", "json")
    data = json.loads(result.stdout)
    assert [(r["word"], r["total"], r["files"]) for r in data["words"]] == [
        ("don't", 2, 1),
        ("go", 2, 2),
        ("quoted", 1, 1),
        ("stop", 1, 1),
    ]
    assert data["words"][0]["counts"] == {"a.txt": 2, "b.txt": 0}
    assert data["per_file"] == [
        {"file": "a.txt", "words": 4, "unique": 3, "exclusive": 2},
        {"file": "b.txt", "words": 2, "unique": 2, "exclusive": 1},
    ]
    assert data["totals"] == {
        "files": 2,
        "words": 6,
        "unique": 4,
        "shared": 1,
        "exclusive": 3,
        "shown": 4,
        "hidden": 0,
    }


def test_D1_three_files(tmp_path):
    put(tmp_path, "a.txt", "x y")
    put(tmp_path, "b.txt", "x")
    put(tmp_path, "c.txt", "z")
    result = compare(tmp_path, "a.txt", "b.txt", "c.txt")
    assert result.returncode == 0
    assert norm(result.stdout) == """\
== words ==
word a.txt b.txt c.txt total files
x 1 1 0 2 2
y 1 0 0 1 1
z 0 0 1 1 1

== per_file ==
file words unique exclusive
a.txt 2 2 1
b.txt 1 1 0
c.txt 1 1 1

== totals ==
files 3
words 4
unique 3
shared 1
exclusive 2
shown 3
hidden 0"""


def test_D1_exclusive_means_found_in_no_other_file(tmp_path):
    put(tmp_path, "a.txt", "p p q")
    put(tmp_path, "b.txt", "q r")
    put(tmp_path, "c.txt", "r s")
    data = json.loads(compare(tmp_path, "a.txt", "b.txt", "c.txt", "--format", "json").stdout)
    assert data["per_file"] == [
        {"file": "a.txt", "words": 3, "unique": 2, "exclusive": 1},
        {"file": "b.txt", "words": 2, "unique": 2, "exclusive": 0},
        {"file": "c.txt", "words": 2, "unique": 2, "exclusive": 1},
    ]
    assert data["totals"]["unique"] == 4
    assert data["totals"]["shared"] == 2
    assert data["totals"]["exclusive"] == 2


# ---------------- D2 ----------------


def test_D2_json_all_sections(ab):
    result = compare(ab, "a.txt", "b.txt", "--format", "json")
    assert result.returncode == 0
    assert json.loads(result.stdout) == D1_JSON
    assert [r["word"] for r in json.loads(result.stdout)["words"]] == [
        "the",
        "cat",
        "sat",
        "dog",
    ]


def test_D2_csv_all_sections(ab):
    result = compare(ab, "a.txt", "b.txt", "--format", "csv")
    assert result.returncode == 0
    assert norm(result.stdout) == D1_CSV


def test_D2_tsv_all_sections(ab):
    result = compare(ab, "a.txt", "b.txt", "--format", "tsv")
    assert result.returncode == 0
    assert norm(result.stdout) == D1_TSV


def test_D2_markdown_all_sections(ab):
    result = compare(ab, "a.txt", "b.txt", "--format", "markdown")
    assert result.returncode == 0
    sections = parse_sections("markdown", result.stdout)
    assert list(sections) == ["words", "per_file", "totals"]
    assert sections == expected_sections("markdown")
    assert "| name | value |" in norm(result.stdout).split("\n")


def test_D2_markdown_blank_line_between_sections(ab):
    out = norm(compare(ab, "a.txt", "b.txt", "--format", "markdown").stdout)
    assert "\n\n## per_file\n" in out
    assert "\n\n## totals\n" in out


def test_D2_explicit_text_format_matches_default(ab):
    result = compare(ab, "a.txt", "b.txt", "--format", "text")
    assert norm(result.stdout) == D1_TEXT


@pytest.mark.parametrize("fmt", ["text", "csv", "tsv", "markdown"])
@pytest.mark.parametrize("section", ["words", "per_file", "totals"])
def test_D2_section_selects_one_section(ab, fmt, section):
    result = compare(ab, "a.txt", "b.txt", "--format", fmt, "--section", section)
    assert result.returncode == 0
    sections = parse_sections(fmt, result.stdout)
    assert list(sections) == [section]
    assert sections[section] == expected_sections(fmt)[section]


@pytest.mark.parametrize("section", ["words", "per_file", "totals"])
def test_D2_json_section_selects_one_section(ab, section):
    result = compare(ab, "a.txt", "b.txt", "--format", "json", "--section", section)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    others = {"words", "per_file", "totals"} - {section}
    assert section in data
    assert data[section] == D1_JSON[section]
    assert not (others & set(data))


@pytest.mark.parametrize("fmt", ["text", "csv", "tsv", "markdown", "json"])
def test_D2_section_all_equals_default(ab, fmt):
    default = compare(ab, "a.txt", "b.txt", "--format", fmt)
    explicit = compare(ab, "a.txt", "b.txt", "--format", fmt, "--section", "all")
    assert explicit.returncode == 0
    assert explicit.stdout == default.stdout
    assert "totals" in explicit.stdout


def test_D2_csv_quotes_field_only_when_needed(tmp_path):
    put(tmp_path, "x,y.txt", "the cat the cat sat")
    put(tmp_path, "b.txt", "the dog sat")
    result = compare(tmp_path, "x,y.txt", "b.txt", "--format", "csv")
    assert result.returncode == 0
    lines = norm(result.stdout).split("\n")
    assert 'word,"x,y.txt",b.txt,total,files' in lines
    assert '"x,y.txt",5,3,1' in lines
    assert "the,2,1,3,2" in lines
    assert "b.txt,3,3,1" in lines
    sections = parse_sections("csv", result.stdout)
    assert sections["words"][0] == ["word", "x,y.txt", "b.txt", "total", "files"]
    assert sections["per_file"][1] == ["x,y.txt", "5", "3", "1"]


def test_D2_tsv_does_not_quote_commas(tmp_path):
    put(tmp_path, "x,y.txt", "the cat the cat sat")
    put(tmp_path, "b.txt", "the dog sat")
    result = compare(tmp_path, "x,y.txt", "b.txt", "--format", "tsv")
    lines = norm(result.stdout).split("\n")
    assert "word\tx,y.txt\tb.txt\ttotal\tfiles" in lines
    assert "x,y.txt\t5\t3\t1" in lines


def test_D2_unknown_format_exits_2(ab):
    result = compare(ab, "a.txt", "b.txt", "--format", "xml")
    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr.startswith("tally: unknown --format value: xml")


def test_D2_empty_format_exits_2(ab):
    result = compare(ab, "a.txt", "b.txt", "--format", "")
    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr.startswith("tally: unknown --format value: ")


def test_D2_unknown_section_exits_2(ab):
    result = compare(ab, "a.txt", "b.txt", "--section", "nope")
    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr.startswith("tally: unknown --section value: nope")


def test_D2_table_format_is_not_a_compare_format(ab):
    result = compare(ab, "a.txt", "b.txt", "--format", "table")
    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr.startswith("tally: unknown --format value: table")


# ---------------- D3 ----------------


def test_D3_default_sort_is_total(ab):
    assert word_order(compare(ab, "a.txt", "b.txt", "--format", "json")) == [
        "the",
        "cat",
        "sat",
        "dog",
    ]


def test_D3_sort_total_explicit(ab):
    result = compare(ab, "a.txt", "b.txt", "--format", "json", "--sort", "total")
    assert word_order(result) == ["the", "cat", "sat", "dog"]


def test_D3_sort_alpha(ab):
    result = compare(ab, "a.txt", "b.txt", "--format", "json", "--sort", "alpha")
    assert result.returncode == 0
    assert word_order(result) == ["cat", "dog", "sat", "the"]


def test_D3_sort_files(ab):
    result = compare(ab, "a.txt", "b.txt", "--format", "json", "--sort", "files")
    assert result.returncode == 0
    assert word_order(result) == ["sat", "the", "cat", "dog"]


def test_D3_sort_spread(ab):
    result = compare(ab, "a.txt", "b.txt", "--format", "json", "--sort", "spread")
    assert result.returncode == 0
    assert word_order(result) == ["cat", "dog", "the", "sat"]


def test_D3_sort_spread_text_output(ab):
    result = compare(ab, "a.txt", "b.txt", "--sort", "spread", "--section", "words")
    assert norm(result.stdout) == """\
== words ==
word a.txt b.txt total files
cat 2 0 2 1
dog 0 1 1 1
the 2 1 3 2
sat 1 1 2 2"""


def test_D3_spread_uses_highest_minus_lowest_over_all_files(tmp_path):
    put(tmp_path, "a.txt", "x x x x a")
    put(tmp_path, "b.txt", "x x x x b")
    result = compare(tmp_path, "a.txt", "b.txt", "--format", "json", "--sort", "spread")
    assert word_order(result) == ["a", "b", "x"]
    default = compare(tmp_path, "a.txt", "b.txt", "--format", "json")
    assert word_order(default) == ["x", "a", "b"]


def test_D3_files_sort_with_three_files_ties_alpha(tmp_path):
    put(tmp_path, "a.txt", "m n o")
    put(tmp_path, "b.txt", "m n")
    put(tmp_path, "c.txt", "m p")
    result = compare(tmp_path, "a.txt", "b.txt", "c.txt", "--format", "json", "--sort", "files")
    assert word_order(result) == ["m", "n", "o", "p"]


def test_D3_sort_applies_to_other_formats(ab):
    result = compare(ab, "a.txt", "b.txt", "--format", "csv", "--sort", "alpha", "--section", "words")
    rows = parse_sections("csv", result.stdout)["words"]
    assert [row[0] for row in rows] == ["word", "cat", "dog", "sat", "the"]


def test_D3_sort_does_not_change_other_sections(ab):
    result = compare(ab, "a.txt", "b.txt", "--format", "json", "--sort", "alpha")
    data = json.loads(result.stdout)
    assert data["per_file"] == D1_JSON["per_file"]
    assert data["totals"] == D1_JSON["totals"]


def test_D3_unknown_sort_exits_2(ab):
    result = compare(ab, "a.txt", "b.txt", "--sort", "random")
    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr != ""


def test_D3_count_is_not_a_compare_sort(ab):
    result = compare(ab, "a.txt", "b.txt", "--sort", "count")
    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr != ""


# ---------------- D4 ----------------


def filtered(tmp_path, *opts):
    result = compare(tmp_path, "a.txt", "b.txt", "--format", "json", *opts)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def check_rest_unchanged(data, shown, hidden):
    assert data["per_file"] == D1_JSON["per_file"]
    expected = dict(D1_JSON["totals"], shown=shown, hidden=hidden)
    assert data["totals"] == expected


def test_D4_min_total(ab):
    data = filtered(ab, "--min-total", "2")
    assert [r["word"] for r in data["words"]] == ["the", "cat", "sat"]
    check_rest_unchanged(data, 3, 1)


def test_D4_min_total_is_inclusive_and_strict_above(ab):
    data = filtered(ab, "--min-total", "3")
    assert [r["word"] for r in data["words"]] == ["the"]
    check_rest_unchanged(data, 1, 3)


def test_D4_min_files(ab):
    data = filtered(ab, "--min-files", "2")
    assert [r["word"] for r in data["words"]] == ["the", "sat"]
    check_rest_unchanged(data, 2, 2)


def test_D4_min_total_and_min_files_both_hold(ab):
    data = filtered(ab, "--min-total", "3", "--min-files", "2")
    assert [r["word"] for r in data["words"]] == ["the"]
    check_rest_unchanged(data, 1, 3)


def test_D4_both_minimums_exclude_what_either_excludes(ab):
    data = filtered(ab, "--min-total", "2", "--min-files", "2")
    assert [r["word"] for r in data["words"]] == ["the", "sat"]
    check_rest_unchanged(data, 2, 2)


def test_D4_min_files_one_and_min_total_one_keep_everything(ab):
    data = filtered(ab, "--min-total", "1", "--min-files", "1")
    assert data == D1_JSON


def test_D4_minimum_above_every_word_leaves_empty_words(ab):
    result = compare(ab, "a.txt", "b.txt", "--format", "json", "--min-total", "99")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["words"] == []
    check_rest_unchanged(data, 0, 4)


def test_D4_min_files_above_file_count_leaves_empty_words(ab):
    data = filtered(ab, "--min-files", "3")
    assert data["words"] == []
    check_rest_unchanged(data, 0, 4)


def test_D4_filter_keeps_sort(ab):
    data = filtered(ab, "--min-total", "2", "--sort", "alpha")
    assert [r["word"] for r in data["words"]] == ["cat", "sat", "the"]
    check_rest_unchanged(data, 3, 1)


def test_D4_text_totals_reflect_filter(ab):
    result = compare(ab, "a.txt", "b.txt", "--min-files", "2", "--section", "totals")
    assert norm(result.stdout) == """\
== totals ==
files 2
words 8
unique 4
shared 2
exclusive 2
shown 2
hidden 2"""


def test_D4_text_words_rows_after_filter(ab):
    result = compare(ab, "a.txt", "b.txt", "--min-total", "2", "--section", "words")
    assert norm(result.stdout) == """\
== words ==
word a.txt b.txt total files
the 2 1 3 2
cat 2 0 2 1
sat 1 1 2 2"""


@pytest.mark.parametrize("option", ["--min-total", "--min-files"])
@pytest.mark.parametrize("value", ["0", "-1", "x", "1.5", ""])
def test_D4_invalid_minimum_exits_2(ab, option, value):
    result = compare(ab, "a.txt", "b.txt", option, value)
    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr != ""


# ---------------- D5 ----------------


def test_D5_missing_file_named_and_others_compared(ab):
    result = compare(ab, "a.txt", "missing.txt", "b.txt")
    assert result.returncode == 2
    assert "missing.txt" in result.stderr
    assert norm(result.stdout) == D1_TEXT
    assert "missing.txt" not in result.stdout


def test_D5_not_utf8_file_named_and_others_compared(ab):
    put(ab, "bad.txt", b"\xff\xfe\xfa")
    result = compare(ab, "a.txt", "bad.txt", "b.txt", "--format", "json")
    assert result.returncode == 2
    assert "bad.txt" in result.stderr
    assert json.loads(result.stdout) == D1_JSON


def test_D5_only_one_readable_file_exits_2(ab):
    result = compare(ab, "a.txt", "missing.txt")
    assert result.returncode == 2
    assert result.stdout == ""
    assert "missing.txt" in result.stderr


def test_D5_only_one_readable_file_when_other_not_utf8(ab):
    put(ab, "bad.txt", b"\xff\xfe\xfa")
    result = compare(ab, "bad.txt", "a.txt")
    assert result.returncode == 2
    assert result.stdout == ""
    assert "bad.txt" in result.stderr


def test_D5_no_readable_file_exits_2(tmp_path):
    result = compare(tmp_path, "one.txt", "two.txt")
    assert result.returncode == 2
    assert result.stdout == ""
    assert "one.txt" in result.stderr
    assert "two.txt" in result.stderr


def test_D5_single_file_exits_2(ab):
    result = compare(ab, "a.txt")
    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr != ""


def test_D5_repeated_file_name_exits_2(ab):
    result = compare(ab, "a.txt", "b.txt", "a.txt")
    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr != ""


def test_D5_repeated_file_name_only_exits_2(ab):
    result = compare(ab, "a.txt", "a.txt")
    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr != ""


def test_D5_no_file_exits_2(tmp_path):
    result = compare(tmp_path)
    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr != ""
    assert "No such file" not in result.stderr


def test_D5_options_but_no_file_exits_2(tmp_path):
    result = compare(tmp_path, "--format", "json")
    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr != ""
    assert "No such file" not in result.stderr


def test_D5_unknown_option_exits_2(ab):
    result = compare(ab, "a.txt", "b.txt", "--bogus")
    assert result.returncode == 2
    assert result.stdout == ""
    assert "--bogus" in result.stderr


def test_D5_unknown_option_before_files_exits_2(ab):
    result = compare(ab, "--bogus", "a.txt", "b.txt")
    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr != ""


def test_D5_top_option_is_unknown_to_compare(ab):
    result = compare(ab, "a.txt", "b.txt", "--top", "3")
    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr != ""


def test_D5_no_words_exits_1(tmp_path):
    put(tmp_path, "a.txt", "123 !!! 42")
    put(tmp_path, "b.txt", "")
    result = compare(tmp_path, "a.txt", "b.txt")
    assert result.returncode == 1
    assert result.stdout == ""
    assert "tally: no words" in result.stderr


def test_D5_words_in_one_file_only_is_not_an_error(tmp_path):
    put(tmp_path, "a.txt", "alpha beta")
    put(tmp_path, "b.txt", "")
    result = compare(tmp_path, "a.txt", "b.txt", "--format", "json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["per_file"] == [
        {"file": "a.txt", "words": 2, "unique": 2, "exclusive": 2},
        {"file": "b.txt", "words": 0, "unique": 0, "exclusive": 0},
    ]
    assert data["totals"]["shared"] == 0
    assert data["totals"]["exclusive"] == 2


# ---------------- D6 (stays) ----------------


def test_D6_single_file_counts_stay(ab):
    result = run_tally("a.txt", cwd=ab)
    assert result.returncode == 0
    assert result.stdout == "0 5 19 a.txt\n"


def test_D6_two_files_counts_stay(ab):
    result = run_tally("a.txt", "b.txt", cwd=ab)
    assert result.returncode == 0
    assert result.stdout == "0 5 19 a.txt\n0 3 11 b.txt\n0 8 30 total\n"


def test_D6_top_stays(ab):
    result = run_tally("--top", "3", "a.txt", cwd=ab)
    assert result.returncode == 0
    assert result.stdout == "cat 2\nthe 2\nsat 1\n"


def test_D6_top_csv_alpha_stays(ab):
    result = run_tally("--top", "3", "--format", "csv", "--sort", "alpha", "a.txt", cwd=ab)
    assert result.returncode == 0
    assert result.stdout == "word,count\ncat,2\nsat,1\nthe,2\n"


def test_D6_compare_not_first_argument_is_not_routed(ab):
    result = run_tally("a.txt", "--compare", cwd=ab)
    assert result.returncode == 2
    assert result.stdout == "0 5 19 a.txt\n0 5 19 total\n"
    assert "--compare" in result.stderr
