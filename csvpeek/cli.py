"""The command line: csvpeek file.csv [--rows N] [--delimiter X] [--no-sample]."""

import argparse
import sys

from . import VERSION, core, report


def build_parser():
    p = argparse.ArgumentParser(
        prog="csvpeek",
        description="Instant CSV/TSV inspection: shape, types, nulls, stats, sample rows.")
    p.add_argument("file", help="the CSV/TSV file to inspect, or - for stdin")
    p.add_argument("--rows", type=int, default=5, metavar="N",
                   help="sample rows to print (default 5, 0 for none)")
    p.add_argument("--delimiter", metavar="X",
                   help="force a delimiter instead of sniffing (e.g. ';' or 'TAB')")
    p.add_argument("--encoding", default="utf-8-sig",
                   help="file encoding (default utf-8-sig, which also eats a BOM)")
    p.add_argument("--width", type=int, default=100,
                   help="wrap the report to this many columns (default 100)")
    p.add_argument("--version", action="version", version="csvpeek " + VERSION)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    delimiter = args.delimiter
    if delimiter and delimiter.upper() == "TAB":
        delimiter = "\t"
    def note_encoding(used):
        print("csvpeek: note: BOM says %s; using it instead of %s"
              % (used, args.encoding), file=sys.stderr)
    try:
        if args.file == "-":
            header, rows = core.read_rows(sys.stdin, delimiter=delimiter)
        else:
            header, rows = core.read_rows(args.file, delimiter=delimiter,
                                          encoding=args.encoding,
                                          on_encoding=note_encoding)
    except OSError as e:
        print("csvpeek: cannot read %s: %s" % (args.file, e), file=sys.stderr)
        return 2
    except ValueError as e:
        print("csvpeek: %s" % e, file=sys.stderr)
        return 2
    if not header:
        print("csvpeek: %s is empty" % args.file, file=sys.stderr)
        return 1
    summary = core.summarize(header, rows)
    sample = rows[:args.rows] if args.rows > 0 else None
    print(report.render(summary, sample_rows=sample, header=header, width=args.width))
    return 0


if __name__ == "__main__":
    sys.exit(main())
