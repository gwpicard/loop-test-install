import json
import re
import sys
from collections import Counter

from tally.cli import read_text

FORMATS = ("text", "json", "csv", "markdown")
SORTS = ("count", "alpha", "files")
VALUE_OPTIONS = ("--format", "--sort", "--min-count")
USAGE = "usage: tally --report [--format F] [--sort S] [--min-count N] [--no-summary] <file>..."
SORT_KEYS = {
    "count": lambda row: (-row[1], row[0]),
    "alpha": lambda row: row[0],
    "files": lambda row: (-row[2], row[0]),
}


def fail(message):
    print(message, file=sys.stderr)
    return None


def split_args(args):
    options = {"--no-summary": False}
    files = []
    remaining = iter(args)
    for arg in remaining:
        if arg == "--no-summary":
            options[arg] = True
        elif arg in VALUE_OPTIONS:
            value = next(remaining, None)
            if value is None:
                return None
            options[arg] = value
        else:
            files.append(arg)
    return options, files


def check_min_count(value):
    if not value.isascii() or not value.isdigit() or int(value) < 1:
        return fail("tally: --min-count needs a whole number of at least 1")
    return int(value)


def check_choice(options, name, allowed, default):
    value = options.get(name, default)
    if value not in allowed:
        return fail(f"tally: unknown {name} value: {value}")
    return value


def parse_report(args):
    if "--top" in args:
        return fail("tally: --top cannot be used with --report")
    parsed = split_args(args)
    if parsed is None or not parsed[1]:
        return fail(USAGE)
    options, files = parsed
    fmt = check_choice(options, "--format", FORMATS, "text")
    order = check_choice(options, "--sort", SORTS, "count")
    minimum = check_min_count(options.get("--min-count", "1"))
    if fmt is None or order is None or minimum is None:
        return None
    return files, fmt, order, minimum, not options["--no-summary"]


def tally_files(files):
    counts = Counter()
    spread = Counter()
    read = 0
    for name in files:
        text = read_text(name)
        if text is None:
            continue
        words = re.findall(r"[a-z]+(?:'[a-z]+)*", text.lower())
        read += 1
        counts.update(words)
        spread.update(set(words))
    return counts, spread, read, read < len(files)


def build_rows(counts, spread, minimum, order):
    rows = [(word, n, spread[word]) for word, n in counts.items() if n >= minimum]
    rows.sort(key=SORT_KEYS[order])
    return rows


def build_summary(counts, read, shown):
    return {
        "files": read,
        "words": sum(counts.values()),
        "unique": len(counts),
        "shown": shown,
        "hidden": len(counts) - shown,
    }


def lines_text(rows, summary):
    lines = ["word count files"] + [f"{w} {c} {f}" for w, c, f in rows]
    if summary:
        lines += [""] + [f"{key}: {value}" for key, value in summary.items()]
    return lines


def lines_csv(rows, summary):
    return ["word,count,files"] + [f"{w},{c},{f}" for w, c, f in rows]


def lines_json(rows, summary):
    data = {"rows": [{"word": w, "count": c, "files": f} for w, c, f in rows]}
    if summary:
        data["summary"] = summary
    return [json.dumps(data)]


def lines_markdown(rows, summary):
    lines = ["| word | count | files |", "| --- | --- | --- |"]
    lines += [f"| {w} | {c} | {f} |" for w, c, f in rows]
    if summary:
        lines += ["", "## Summary", ""]
        lines += [f"- {key}: {value}" for key, value in summary.items()]
    return lines


LINE_BUILDERS = {
    "text": lines_text,
    "csv": lines_csv,
    "json": lines_json,
    "markdown": lines_markdown,
}


def run_report(args):
    settings = parse_report(args)
    if settings is None:
        return 2
    files, fmt, order, minimum, with_summary = settings
    counts, spread, read, failed = tally_files(files)
    if not counts:
        print("tally: no words", file=sys.stderr)
        return 1
    rows = build_rows(counts, spread, minimum, order)
    summary = build_summary(counts, read, len(rows)) if with_summary else None
    for line in LINE_BUILDERS[fmt](rows, summary):
        print(line)
    return 2 if failed else 0
