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


def parse_top(args):
    if len(args) != 3:
        print("usage: tally --top N <file>", file=sys.stderr)
        return None
    if not args[1].isascii() or not args[1].isdigit() or int(args[1]) < 1:
        print("tally: --top needs a whole number of at least 1", file=sys.stderr)
        return None
    return int(args[1])


def print_top(text, top, name):
    words = re.findall(r"[a-z]+", text.lower())
    if not words:
        print(f"tally: {name}: no words", file=sys.stderr)
        return 1
    counts = sorted(Counter(words).items(), key=lambda item: (-item[1], item[0]))
    for word, count in counts[:top]:
        print(f"{word} {count}")
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
    top = parse_top(args)
    if top is None:
        return 2
    text = read_text(args[2])
    if text is None:
        return 2
    return print_top(text, top, args[2])


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if args and args[0] == "--top":
        return run_top(args)
    if not args:
        print("usage: tally <file>", file=sys.stderr)
        return 2
    return print_counts(args)
