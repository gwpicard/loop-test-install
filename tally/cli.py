import json
import re
import sys
from collections import Counter
from typing import NamedTuple


def read_text(name):
    try:
        with open(name, "rb") as f:
            return f.read().decode("utf-8")
    except OSError as error:
        print(f"tally: {name}: {error.strerror}", file=sys.stderr)
    except UnicodeDecodeError:
        print(f"tally: {name}: not valid UTF-8", file=sys.stderr)
    return None


def count_text(text):
    return text.count(chr(10)), len(text.split()), len(text)


FORMATS = ("csv", "json", "table")
SORTS = ("count", "alpha")
OPTION_NAMES = ("--top", "--format", "--sort", "--min-count", "--min-length")
FLAG_NAMES = ("--summary", "--longest-first")
TOP_USAGE = "usage: tally --top N <file>"


class Settings(NamedTuple):
    top: int
    min_count: int
    min_length: int
    fmt: str
    order: str
    summary: bool
    longest: bool


def split_args(args):
    options = {}
    index = 0
    while index < len(args) and args[index].startswith("--"):
        name = args[index]
        if name in FLAG_NAMES:
            options[name] = True
            index += 1
        elif name in OPTION_NAMES and args[index + 1 :]:
            options[name] = args[index + 1]
            index += 2
        else:
            return None
    return (options, args[index:]) if "--top" in options else None


def check_number(options, name):
    value = options.get(name, "1")
    if not value.isascii() or not value.isdigit() or int(value) < 1:
        print(f"tally: {name} needs a whole number of at least 1", file=sys.stderr)
        return None
    return int(value)


def check_choice(options, name, allowed):
    value = options.get(name)
    if value is not None and value not in allowed:
        message = " or ".join(", ".join(allowed).rsplit(", ", 1))
        print(f"tally: unknown {name} value: {value} (use {message})", file=sys.stderr)
        return False
    return True


def check_choices(options):
    return check_choice(options, "--format", FORMATS) and check_choice(
        options, "--sort", SORTS
    )


def read_settings(options):
    names = ("--top", "--min-count", "--min-length")
    numbers = [check_number(options, name) for name in names]
    if None in numbers or not check_choices(options):
        return None
    fmt, order = options.get("--format"), options.get("--sort")
    flags = (options.get("--summary") is True, options.get("--longest-first") is True)
    return Settings(*numbers, fmt, order, *flags)


def parse_top(args, usage=TOP_USAGE, many=False):
    split = split_args(args)
    if split is None or not split[1] or (len(split[1]) > 1 and not many):
        print(usage, file=sys.stderr)
        return None
    settings = read_settings(split[0])
    return None if settings is None else (settings, split[1])


def format_plain(rows):
    return [" ".join((word, str(count))) for word, count in rows]


def format_csv(rows):
    return ["word,count"] + [f"{word},{count}" for word, count in rows]


def json_rows(rows):
    return [{"word": word, "count": count} for word, count in rows]


def format_json(rows):
    return [json.dumps(json_rows(rows))]


def format_table(rows):
    width = max([4] + [len(word) for word, _ in rows])
    size = max([5] + [len(str(count)) for _, count in rows])
    cells = [("word", "count"), ("-" * width, "-" * size)]
    cells += [(word, str(count)) for word, count in rows]
    return [f"{word:<{width}}  {count:>{size}}" for word, count in cells]


FORMATTERS = {
    None: format_plain,
    "csv": format_csv,
    "json": format_json,
    "table": format_table,
}


def summary_values(summary):
    words, unique, shown = summary
    return {"words": words, "unique": unique, "shown": shown, "hidden": unique - shown}


def summary_line(summary):
    values = summary_values(summary)
    return "summary: " + " ".join(f"{key}={value}" for key, value in values.items())


def format_summary(rows, fmt, summary):
    if fmt == "json":
        data = {"rows": json_rows(rows), "summary": summary_values(summary)}
        return [json.dumps(data)]
    lines = FORMATTERS[fmt](rows)
    if fmt == "csv":
        return lines + ["# " + summary_line(summary)]
    if fmt == "table":
        lines.append("")
    return lines + [summary_line(summary)]


def choose_rows(counts, settings):
    rows = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    rows = rows[: settings.top]
    if settings.order == "alpha":
        rows.sort()
    if settings.longest:
        rows.sort(key=lambda item: (-len(item[0]), item[0]))
    return rows


def keep_counts(counts, settings):
    return {
        word: count
        for word, count in counts.items()
        if count >= settings.min_count and len(word) >= settings.min_length
    }


def find_words(text):
    return re.findall(r"[a-z]+(?:'[a-z]+)*", text.lower())


def select_rows(words, settings):
    """Return (rows, summary numbers); rows is empty when no word matches."""
    counts = Counter(words)
    rows = choose_rows(keep_counts(counts, settings), settings)
    return rows, (len(words), len(counts), len(rows))


def report_lines(rows, settings, summary):
    if settings.summary:
        return format_summary(rows, settings.fmt, summary)
    return FORMATTERS[settings.fmt](rows)


def report_top(text, settings, name):
    words = find_words(text)
    if not words:
        print(f"tally: {name}: no words", file=sys.stderr)
        return 1
    rows, summary = select_rows(words, settings)
    if not rows:
        print(f"tally: {name}: no words match", file=sys.stderr)
        return 1
    for line in report_lines(rows, settings, summary):
        print(line)
    return 0


def print_counts(names):
    status = 0
    totals = [0, 0, 0]
    for name in names:
        text = read_text(name)
        if text is None:
            status = 2
            continue
        counts = count_text(text)
        totals = [total + count for total, count in zip(totals, counts)]
        print(f"{counts[0]} {counts[1]} {counts[2]} {name}")
    if len(names) > 1:
        print(f"{totals[0]} {totals[1]} {totals[2]} total")
    return status


def run_top(args):
    parsed = parse_top(args)
    if parsed is None:
        return 2
    settings, (name,) = parsed
    text = read_text(name)
    if text is None:
        return 2
    return report_top(text, settings, name)


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if args and args[0] == "--by-file":
        from tally.byfile import run_by_file

        return run_by_file(args[1:])
    if args and args[0] in OPTION_NAMES + FLAG_NAMES and "--top" in args:
        return run_top(args)
    if not args:
        print("usage: tally <file>", file=sys.stderr)
        return 2
    return print_counts(args)
