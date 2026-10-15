import csv
import io
import json
import re
import sys
from collections import Counter

from tally.cli import read_text

FORMATS = ("text", "json", "csv", "markdown", "tsv")
SORTS = ("total", "alpha", "files", "spread")
SECTIONS = ("words", "per_file", "totals")
CHOICES = {
    "--format": FORMATS,
    "--sort": SORTS,
    "--section": SECTIONS + ("all",),
}
MINIMUMS = ("--min-total", "--min-files")
DEFAULTS = {
    "--format": "text",
    "--sort": "total",
    "--section": "all",
    "--min-total": "1",
    "--min-files": "1",
}


def fail(message):
    print(f"tally: {message}", file=sys.stderr)
    return None


def split_args(args):
    options = dict(DEFAULTS)
    names = []
    items = iter(args)
    for item in items:
        if not item.startswith("--"):
            names.append(item)
        elif item not in DEFAULTS:
            return fail(f"unknown option: {item}")
        else:
            value = next(items, None)
            if value is None:
                return fail(f"{item} needs a value")
            options[item] = value
    return options, names


def check_minimum(options, name):
    value = options[name]
    if not value.isascii() or not value.isdigit() or int(value) < 1:
        return fail(f"{name} needs a whole number of at least 1")
    return int(value)


def check_choices(options):
    for name, allowed in CHOICES.items():
        if options[name] not in allowed:
            return fail(f"unknown {name} value: {options[name]} (use {', '.join(allowed)})")
    return True


def check_names(names):
    if len(names) < 2:
        return fail("--compare needs at least two files")
    repeated = sorted({name for name in names if names.count(name) > 1})
    if repeated:
        return fail(f"file named more than once: {', '.join(repeated)}")
    return True


def parse_compare(args):
    parsed = split_args(args)
    if parsed is None:
        return None
    options, names = parsed
    if not check_choices(options) or not check_names(names):
        return None
    minimums = [check_minimum(options, name) for name in MINIMUMS]
    if None in minimums:
        return None
    return options, names, minimums


def read_files(names):
    texts = {name: read_text(name) for name in names}
    return {name: text for name, text in texts.items() if text is not None}


def count_words(text):
    return Counter(re.findall(r"[a-z]+(?:'[a-z]+)*", text.lower()))


def build_table(counters):
    vocabulary = sorted(set().union(*counters))
    table = []
    for word in vocabulary:
        counts = [counter[word] for counter in counters]
        found = sum(1 for count in counts if count > 0)
        table.append((word, counts, sum(counts), found))
    return table


def filter_table(table, min_total, min_files):
    return [row for row in table if row[2] >= min_total and row[3] >= min_files]


SORT_KEYS = {
    "total": lambda row: (-row[2], row[0]),
    "alpha": lambda row: row[0],
    "files": lambda row: (-row[3], row[0]),
    "spread": lambda row: (min(row[1]) - max(row[1]), row[0]),
}


def sort_table(table, order):
    return sorted(table, key=SORT_KEYS[order])


def build_per_file(counters, table):
    exclusive = [0] * len(counters)
    for _, counts, _, found in table:
        if found == 1:
            exclusive[[count > 0 for count in counts].index(True)] += 1
    return [
        (sum(counter.values()), len(counter), only)
        for counter, only in zip(counters, exclusive)
    ]


def build_totals(counters, table, shown):
    shared = sum(1 for row in table if row[3] >= 2)
    return [
        ("files", len(counters)),
        ("words", sum(sum(counter.values()) for counter in counters)),
        ("unique", len(table)),
        ("shared", shared),
        ("exclusive", len(table) - shared),
        ("shown", shown),
        ("hidden", len(table) - shown),
    ]


def build_tables(labels, words, per_file, totals):
    return {
        "words": (
            ["word", *labels, "total", "files"],
            [[word, *counts, total, found] for word, counts, total, found in words],
        ),
        "per_file": (
            ["file", "words", "unique", "exclusive"],
            [[label, *values] for label, values in zip(labels, per_file)],
        ),
        "totals": (["name", "value"], [list(pair) for pair in totals]),
    }


def format_text(tables):
    blocks = []
    for name, (header, rows) in tables.items():
        lines = [f"== {name} =="]
        lines += [" ".join(map(str, row)) for row in ([] if name == "totals" else [header]) + rows]
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def format_csv(tables):
    blocks = []
    for name, (header, rows) in tables.items():
        buffer = io.StringIO()
        csv.writer(buffer, lineterminator="\n").writerows([header] + rows)
        blocks.append(f"# {name}\n" + buffer.getvalue()[:-1])
    return "\n\n".join(blocks)


def format_tsv(tables):
    blocks = []
    for name, (header, rows) in tables.items():
        lines = ["\t".join(map(str, row)) for row in [header] + rows]
        blocks.append("\n".join([f"# {name}"] + lines))
    return "\n\n".join(blocks)


def markdown_row(cells):
    return "| " + " | ".join(map(str, cells)) + " |"


def format_markdown(tables):
    blocks = []
    for name, (header, rows) in tables.items():
        lines = [f"## {name}", "", markdown_row(header), markdown_row(["---"] * len(header))]
        lines += [markdown_row(row) for row in rows]
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def format_json(tables, labels):
    data = {"files": labels}
    for name, (header, rows) in tables.items():
        data[name] = json_section(name, labels, rows)
    return json.dumps(data)


def json_section(name, labels, rows):
    if name == "words":
        return [
            {"word": row[0], "counts": dict(zip(labels, row[1:-2])), "total": row[-2], "files": row[-1]}
            for row in rows
        ]
    if name == "per_file":
        return [dict(zip(("file", "words", "unique", "exclusive"), row)) for row in rows]
    return {key: value for key, value in rows}


def render(tables, labels, fmt):
    if fmt == "json":
        return format_json(tables, labels)
    return {
        "text": format_text,
        "csv": format_csv,
        "tsv": format_tsv,
        "markdown": format_markdown,
    }[fmt](tables)


def select_sections(tables, section):
    if section == "all":
        return tables
    return {section: tables[section]}


def run_compare(args):
    parsed = parse_compare(args)
    if parsed is None:
        return 2
    options, names, (min_total, min_files) = parsed
    texts = read_files(names)
    status = 0 if len(texts) == len(names) else 2
    if len(texts) < 2:
        return 2
    labels = list(texts)
    counters = [count_words(text) for text in texts.values()]
    full = build_table(counters)
    if not full:
        print("tally: no words", file=sys.stderr)
        return 1
    words = sort_table(filter_table(full, min_total, min_files), options["--sort"])
    tables = build_tables(
        labels, words, build_per_file(counters, full), build_totals(counters, full, len(words))
    )
    tables = select_sections(tables, options["--section"])
    print(render(tables, labels, options["--format"]))
    return status
