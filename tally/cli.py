import sys


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: tally <file>", file=sys.stderr)
        return 2
    name = args[0]
    try:
        with open(name, "rb") as f:
            text = f.read().decode("utf-8")
    except OSError as error:
        print(f"tally: {name}: {error.strerror}", file=sys.stderr)
        return 2
    except UnicodeDecodeError:
        print(f"tally: {name}: not valid UTF-8", file=sys.stderr)
        return 2
    print(f"{text.count(chr(10))} {len(text.split())} {len(text)} {name}")
    return 0
