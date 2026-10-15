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
    """Return (entry, status); entry is None when the file has no rows."""
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
        return None, 1
    return (name, rows, summary), 0


def json_entry(entry, settings):
    name, rows, summary = entry
    data = {"file": name, "rows": json_rows(rows)}
    if settings.summary:
        data["summary"] = summary_values(summary)
    return data


def text_blocks(entries, settings):
    return [
        [f"==> {name} <=="] + report_lines(rows, settings, summary)
        for name, rows, summary in entries
    ]


def print_entries(entries, settings):
    if settings.fmt == "json":
        data = {"files": [json_entry(entry, settings) for entry in entries]}
        print(json.dumps(data))
        return
    for index, block in enumerate(text_blocks(entries, settings)):
        if index:
            print()
        for line in block:
            print(line)


def exit_code(statuses):
    return 2 if 2 in statuses else max(statuses, default=0)


def run_by_file(args):
    parsed = parse_top(args, USAGE, many=True)
    if parsed is None:
        return 2
    settings, names = parsed
    results = [file_report(name, settings) for name in names]
    entries = [entry for entry, _ in results if entry is not None]
    print_entries(entries, settings)
    return exit_code([status for _, status in results])
