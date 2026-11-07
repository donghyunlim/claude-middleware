import sys

from .report import build_report


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print("usage: python3 -m salesreport.cli DATA_DIR OUT_PATH")
        return 2
    text = build_report(argv[0])
    with open(argv[1], "w", encoding="utf-8", newline="") as f:
        f.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
