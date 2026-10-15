import json
import re
import sys
from collections import Counter


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


def parse_options(args):
    if len(args) % 2 == 0 or len(args) > 7:
        return None
    options = {}
    for name, value in zip(args[0:-1:2], args[1:-1:2]):
        if name not in ("--top", "--format", "--sort"):
            return None
        options[name] = value
    return options if "--top" in options else None


def check_top(value):
    if not value.isascii() or not value.isdigit() or int(value) < 1:
        print("tally: --top needs a whole number of at least 1", file=sys.stderr)
        return None
    return int(value)


def check_choice(options, name, allowed):
    value = options.get(name)
    if value is not None and value not in allowed:
        message = " or ".join(", ".join(allowed).rsplit(", ", 1))
        print(f"tally: unknown {name} value: {value} (use {message})", file=sys.stderr)
        return False
    return True


def parse_top(args):
    options = parse_options(args)
    if options is None:
        print("usage: tally --top N <file>", file=sys.stderr)
        return None
    top = check_top(options["--top"])
    if top is None:
        return None
    if not check_choice(options, "--format", FORMATS):
        return None
    if not check_choice(options, "--sort", SORTS):
        return None
    return top, options.get("--format"), options.get("--sort", "count")


def format_plain(rows):
    return [f"{word} {count}" for word, count in rows]


def format_csv(rows):
    return ["word,count"] + [f"{word},{count}" for word, count in rows]


def format_json(rows):
    return [json.dumps([{"word": word, "count": count} for word, count in rows])]


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


def print_top(words, settings):
    top, fmt, order = settings
    counts = sorted(Counter(words).items(), key=lambda item: (-item[1], item[0]))[:top]
    if order == "alpha":
        counts.sort()
    for line in FORMATTERS[fmt](counts):
        print(line)
    return 0


def report_top(text, settings, name):
    words = re.findall(r"[a-z]+(?:'[a-z]+)*", text.lower())
    if not words:
        print(f"tally: {name}: no words", file=sys.stderr)
        return 1
    return print_top(words, settings)


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
    settings = parse_top(args)
    if settings is None:
        return 2
    text = read_text(args[-1])
    if text is None:
        return 2
    return report_top(text, settings, args[-1])


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if args and args[0] in ("--top", "--format", "--sort") and "--top" in args:
        return run_top(args)
    if not args:
        print("usage: tally <file>", file=sys.stderr)
        return 2
    return print_counts(args)
