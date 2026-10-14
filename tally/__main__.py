import argparse
import re
import sys
from collections import Counter


def positive_int(text):
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid number: {text!r}")
    if value < 1:
        raise argparse.ArgumentTypeError(f"must be at least 1: {text!r}")
    return value


def main():
    parser = argparse.ArgumentParser(prog="tally")
    parser.add_argument("--top", type=positive_int, metavar="N")
    parser.add_argument("file")
    args = parser.parse_args()

    with open(args.file, encoding="utf-8") as f:
        text = f.read()

    if args.top is None:
        print(text.count("\n"), len(text.split()), len(text))
        return

    words = re.findall(r"[a-z]+", text.lower())
    counts = sorted(Counter(words).items(), key=lambda item: (-item[1], item[0]))
    for word, count in counts[: args.top]:
        print(f"{word} {count}")


if __name__ == "__main__":
    sys.exit(main())
