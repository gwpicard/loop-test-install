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


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    top = None
    if args and args[0] == "--top":
        if len(args) != 3:
            print("usage: tally --top N <file>", file=sys.stderr)
            return 2
        if not args[1].isascii() or not args[1].isdigit() or int(args[1]) < 1:
            print("tally: --top needs a whole number of at least 1", file=sys.stderr)
            return 2
        top = int(args[1])
        args = args[2:]
    if not args:
        print("usage: tally <file>", file=sys.stderr)
        return 2
    if len(args) > 1:
        status = 0
        totals = [0, 0, 0]
        for name in args:
            text = read_text(name)
            if text is None:
                status = 2
                continue
            counts = count_text(text)
            totals = [total + count for total, count in zip(totals, counts)]
            print(f"{counts[0]} {counts[1]} {counts[2]} {name}")
        print(f"{totals[0]} {totals[1]} {totals[2]} total")
        return status
    name = args[0]
    text = read_text(name)
    if text is None:
        return 2
    if top is not None:
        words = re.findall(r"[a-z]+", text.lower())
        counts = sorted(Counter(words).items(), key=lambda item: (-item[1], item[0]))
        for word, count in counts[:top]:
            print(f"{word} {count}")
        return 0
    counts = count_text(text)
    print(f"{counts[0]} {counts[1]} {counts[2]} {name}")
    return 0
