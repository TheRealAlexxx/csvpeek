"""Rendering: the summary dict from core.summarize as a terminal table.

Everything is computed from the summary, so what you see is what the tests
assert. Wide values get ellipsized, numeric stats line up, and the whole
thing stays readable in an 80 column terminal.
"""

ELLIPSIS = "..."


def visible(text):
    """Make control characters visible before text reaches a terminal.

    csvpeek exists to inspect untrusted CSV files. Raw control bytes in a
    cell (ESC in particular) become live ANSI/OSC escape sequences in the
    reader's terminal, which can clear the screen, move the cursor, or -
    with OSC 8/52 - plant clickable hyperlinks or clipboard content.
    Render them as printable \\xNN escapes instead.
    """
    return "".join(
        c if " " <= c != "\x7f" else "\\x%02x" % ord(c) for c in text
    )


def fit(text, width):
    text = visible(str(text))
    if len(text) <= width:
        return text
    if width <= len(ELLIPSIS):
        return text[:width]
    return text[:width - len(ELLIPSIS)] + ELLIPSIS


def fmt_number(value):
    if isinstance(value, float):
        if value == int(value) and abs(value) < 1e15:
            return str(int(value))
        return "%.4g" % value
    return str(value)


def stat_line(col, width):
    """The per-column details after its name and type."""
    parts = []
    if col["nulls"]:
        parts.append("%d null" % col["nulls"])
    parts.append("%d unique" % col["unique"])
    kind = col["type"]
    if kind in ("int", "float"):
        parts.append("min %s" % fmt_number(col["min"]))
        parts.append("max %s" % fmt_number(col["max"]))
        parts.append("mean %s" % fmt_number(round(col["mean"], 4)))
    elif kind == "date":
        parts.append("%s .. %s" % (col["min"], col["max"]))
    elif kind == "bool":
        parts.append("%d true / %d false" % (col["true"], col["false"]))
    if "top" in col and col["top"]:
        tops = ", ".join("%s (%d)" % (fit(v, 16), n) for v, n in col["top"])
        parts.append("top: " + tops)
    return fit("; ".join(parts), width)


def render(summary, sample_rows=None, header=None, width=100, name_width=20):
    """The whole report as a string."""
    lines = []
    lines.append("%d rows x %d columns" % (summary["rows"], summary["cols"]))
    lines.append("")
    for col in summary["columns"]:
        name = fit(col["name"], name_width)
        lines.append("%-*s %-6s %s" % (name_width, name, col["type"], stat_line(col, width - name_width - 8)))
    if sample_rows and header:
        lines.append("")
        lines.append("first rows:")
        col_widths = []
        for i in range(len(header)):
            w = len(str(header[i]))
            for row in sample_rows:
                w = max(w, len(fit(row[i], 24)))
            col_widths.append(min(w, 24))
        lines.append("  ".join(fit(str(h), w).ljust(w) for h, w in zip(header, col_widths)).rstrip())
        lines.append("  ".join("-" * w for w in col_widths).rstrip())
        for row in sample_rows:
            lines.append("  ".join(fit(c, w).ljust(w) for c, w in zip(row, col_widths)).rstrip())
    return "\n".join(lines)
