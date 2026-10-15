import json
import sys

from tally.cli import (
    find_words,
    json_rows,
    parse_top,
    read_text,
    report_lines,
    select_rows,
    summary_values,
)

USAGE = "usage: tally --by-file --top N <file>..."


def file_report(name, settings):
    """Return (entry, status); entry is None when the file is not counted."""
    text = read_text(name)
    if text is None:
        return None, 2
    words = find_words(text)
    if not words:
        print(f"tally: {name}: no words", file=sys.stderr)
        return None, 1
    rows, summary = select_rows(words, settings)
    if not rows:
        print(f"tally: {name}: no words match", file=sys.stderr)
    return (name, rows, summary, set(words)), (0 if rows else 1)


def json_entry(entry, settings):
    name, rows, summary, _ = entry
    data = {"file": name, "rows": json_rows(rows)}
    if settings.summary:
        data["summary"] = summary_values(summary)
    return data


def text_blocks(entries, settings):
    return [
        [f"==> {name} <=="] + report_lines(rows, settings, summary)
        for name, rows, summary, _ in entries
        if rows
    ]


def global_summary(entries):
    vocab = set().union(*[entry[3] for entry in entries])
    shown = {word for entry in entries for word, _ in entry[1]}
    values = {"files": len(entries), "words": sum(entry[2][0] for entry in entries)}
    values.update(unique=len(vocab), shown=len(shown), hidden=len(vocab) - len(shown))
    return values


def global_line(values, fmt):
    text = "summary (all files): " + " ".join(f"{k}={v}" for k, v in values.items())
    return "# " + text if fmt == "csv" else text


def print_json(entries, settings):
    data = {"files": [json_entry(e, settings) for e in entries if e[1]]}
    if settings.summary:
        data["summary"] = global_summary(entries)
    print(json.dumps(data))


def print_entries(entries, settings):
    if settings.fmt == "json":
        return print_json(entries, settings)
    blocks = text_blocks(entries, settings)
    for index, block in enumerate(blocks):
        if index:
            print()
        for line in block:
            print(line)
    if settings.summary:
        if blocks:
            print()
        print(global_line(global_summary(entries), settings.fmt))


def exit_code(statuses):
    return max(statuses, default=0)


def run_by_file(args):
    parsed = parse_top(args, USAGE, many=True)
    if parsed is None:
        return 2
    settings, names = parsed
    results = [file_report(name, settings) for name in names]
    entries = [entry for entry, _ in results if entry is not None]
    print_entries(entries, settings)
    return exit_code([status for _, status in results])
