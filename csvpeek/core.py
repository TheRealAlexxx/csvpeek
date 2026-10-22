"""The inspection engine: sniff, parse, infer, summarize.

Everything here is pure stdlib and pure data in, data out, so the whole
thing is testable without a terminal. Rendering for the terminal lives in
report.py; the command line lives in cli.py.
"""

import csv
import datetime
import io
import re

# values people actually use for "nothing here"
NULL_WORDS = {"", "na", "n/a", "null", "none", "nan", "-", "--", "?", "missing"}

_INT = re.compile(r"^[+-]?\d{1,19}$")
_FLOAT = re.compile(r"^[+-]?(\d+\.\d*|\.\d+|\d+)([eE][+-]?\d+)?$")
_BOOL = {"true", "false", "yes", "no"}
_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d",
                 "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S")


def sniff_dialect(sample, fallback=","):
    """Best guess at the delimiter from the first chunk of the file.

    csv.Sniffer gives up on plenty of real files, so counts of candidate
    delimiters across the sample decide when the sniffer is unsure: the
    winner must appear on most lines, and more than once a line on average.
    """
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        return dialect.delimiter
    except csv.Error:
        pass
    lines = [ln for ln in sample.splitlines() if ln.strip()]
    best, best_score = fallback, 0.0
    for cand in (",", ";", "\t", "|"):
        hits = [ln.count(cand) for ln in lines]
        on_lines = sum(1 for h in hits if h > 0)
        score = (on_lines / max(1, len(lines))) * (sum(hits) / max(1, on_lines or 1))
        if score > best_score:
            best, best_score = cand, score
    return best


def read_rows(source, delimiter=None, encoding="utf-8-sig", sample_bytes=65536):
    """Read a CSV/TSV into (header, rows). utf-8-sig eats a BOM for free.

    source: a path or a file-like object of text.
    """
    if hasattr(source, "read"):
        text = source.read()
        if isinstance(text, bytes):
            text = text.decode(encoding, errors="replace")
    else:
        with open(source, "rb") as f:
            text = f.read().decode(encoding, errors="replace")
    if delimiter is None:
        delimiter = sniff_dialect(text[:sample_bytes])
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = [row for row in reader if any(cell.strip() for cell in row)]
    if not rows:
        return [], []
    header = [h.strip() or "column %d" % (i + 1) for i, h in enumerate(rows[0])]
    body = rows[1:]
    width = len(header)
    normalized = [r + [""] * (width - len(r)) if len(r) < width else r[:width] for r in body]
    return header, normalized


def is_null(value):
    return value.strip().lower() in NULL_WORDS


def parse_number(value):
    """A numeric value as int or float, or None. Thousands separators count
    only when they are consistent (1,234 yes; 1,23 no)."""
    v = value.strip()
    if _INT.match(v):
        try:
            return int(v)
        except ValueError:
            return None
    if re.match(r"^[+-]?\d{1,3}(,\d{3})+$", v):
        return int(v.replace(",", ""))
    if _FLOAT.match(v) and not v.isdigit():
        try:
            return float(v)
        except ValueError:
            return None
    return None


def parse_date(value):
    v = value.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.datetime.strptime(v, fmt)
        except ValueError:
            continue
    return None


def infer_type(values):
    """The column type from its non-null values: bool, int, float, date,
    or string. A column of pure nulls is 'empty'."""
    seen = [v for v in values if not is_null(v)]
    if not seen:
        return "empty"
    low = {v.strip().lower() for v in seen}
    if low <= _BOOL:
        return "bool"
    kinds = set()
    for v in seen:
        n = parse_number(v)
        if n is not None:
            kinds.add("int" if isinstance(n, int) else "float")
            continue
        if parse_date(v) is not None:
            kinds.add("date")
            continue
        return "string"  # one genuine string settles it
    if "float" in kinds:
        return "float"
    if "int" in kinds:
        return "int"
    return "date"


def column_stats(name, values, top=3):
    """Everything the report shows for one column."""
    kind = infer_type(values)
    nulls = sum(1 for v in values if is_null(v))
    unique = len({v.strip() for v in values if not is_null(v)})
    stats = {"name": name, "type": kind, "nulls": nulls, "unique": unique}
    seen = [v for v in values if not is_null(v)]
    if kind in ("int", "float"):
        nums = [parse_number(v) for v in seen]
        stats.update(min=min(nums), max=max(nums), mean=sum(nums) / len(nums))
    elif kind == "date":
        dates = [parse_date(v) for v in seen]
        stats.update(min=min(dates).date().isoformat(), max=max(dates).date().isoformat())
    elif kind == "bool":
        truthy = sum(1 for v in seen if v.strip().lower() in ("true", "yes"))
        stats.update(true=truthy, false=len(seen) - truthy)
    if kind in ("string", "bool") and seen:
        counts = {}
        for v in seen:
            key = v.strip()
            counts[key] = counts.get(key, 0) + 1
        common = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:top]
        stats["top"] = common
    return stats


def summarize(header, rows):
    """The full picture of a parsed file."""
    columns = list(zip(*rows)) if rows else [tuple() for _ in header]
    stats = [column_stats(header[i], list(col)) for i, col in enumerate(columns)]
    return {"rows": len(rows), "cols": len(header), "columns": stats}
