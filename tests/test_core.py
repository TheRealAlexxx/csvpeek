import io
import unittest

from csvpeek import core


class TestSniff(unittest.TestCase):
    def test_comma(self):
        self.assertEqual(core.sniff_dialect("a,b,c\n1,2,3\n4,5,6\n"), ",")

    def test_semicolon_european(self):
        self.assertEqual(core.sniff_dialect("a;b;c\n1;2;3\n4;5;6\n"), ";")

    def test_tab(self):
        self.assertEqual(core.sniff_dialect("a\tb\tc\n1\t2\t3\n"), "\t")

    def test_pipe(self):
        self.assertEqual(core.sniff_dialect("a|b|c\n1|2|3\n"), "|")

    def test_single_column_defaults_to_comma(self):
        self.assertEqual(core.sniff_dialect("name\nalice\nbob\n"), ",")


class TestReadRows(unittest.TestCase):
    def test_basic(self):
        header, rows = core.read_rows(io.StringIO("a,b\n1,2\n3,4\n"))
        self.assertEqual(header, ["a", "b"])
        self.assertEqual(rows, [["1", "2"], ["3", "4"]])

    def test_bom_is_eaten(self):
        header, rows = core.read_rows(io.StringIO("\ufeffname,age\nalice,30\n"))
        self.assertEqual(header, ["name", "age"])

    def test_blank_lines_skipped(self):
        header, rows = core.read_rows(io.StringIO("a,b\n\n1,2\n\n"))
        self.assertEqual(rows, [["1", "2"]])

    def test_ragged_rows_padded(self):
        header, rows = core.read_rows(io.StringIO("a,b,c\n1,2\n3,4,5,6\n"))
        self.assertEqual(rows[0], ["1", "2", ""])
        self.assertEqual(rows[1], ["3", "4", "5"])

    def test_empty_header_cells_named(self):
        header, _ = core.read_rows(io.StringIO("a,,c\n1,2,3\n"))
        self.assertEqual(header, ["a", "column 2", "c"])

    def test_quoted_commas(self):
        header, rows = core.read_rows(io.StringIO('name,note\nalice,"hi, there"\n'))
        self.assertEqual(rows, [["alice", "hi, there"]])

    def test_empty_file(self):
        header, rows = core.read_rows(io.StringIO(""))
        self.assertEqual((header, rows), ([], []))


class TestNumbers(unittest.TestCase):
    def test_int(self):
        self.assertEqual(core.parse_number("42"), 42)
        self.assertEqual(core.parse_number("-7"), -7)

    def test_thousands(self):
        self.assertEqual(core.parse_number("1,234,567"), 1234567)
        self.assertIsNone(core.parse_number("1,23"))

    def test_float(self):
        self.assertEqual(core.parse_number("3.14"), 3.14)
        self.assertEqual(core.parse_number("1e5"), 100000.0)
        self.assertEqual(core.parse_number(".5"), 0.5)

    def test_not_numbers(self):
        for v in ("abc", "12a", "", "1.2.3", "--"):
            self.assertIsNone(core.parse_number(v), v)


class TestDates(unittest.TestCase):
    def test_iso(self):
        self.assertIsNotNone(core.parse_date("2026-10-22"))
        self.assertIsNotNone(core.parse_date("2026-10-22 21:30:00"))

    def test_slashes(self):
        self.assertIsNotNone(core.parse_date("22/10/2026"))

    def test_not_dates(self):
        for v in ("hello", "2026-13-45", "12345"):
            self.assertIsNone(core.parse_date(v), v)


class TestInferType(unittest.TestCase):
    def test_types(self):
        self.assertEqual(core.infer_type(["1", "2", "3"]), "int")
        self.assertEqual(core.infer_type(["1.5", "2", "3"]), "float")
        self.assertEqual(core.infer_type(["yes", "no", "TRUE"]), "bool")
        self.assertEqual(core.infer_type(["2026-01-01", "2026-01-02"]), "date")
        self.assertEqual(core.infer_type(["alice", "bob"]), "string")
        self.assertEqual(core.infer_type(["", "NA", "null"]), "empty")

    def test_one_string_settles_it(self):
        self.assertEqual(core.infer_type(["1", "2", "nope"]), "string")


class TestSummarize(unittest.TestCase):
    def test_full_report_shape(self):
        header, rows = core.read_rows(io.StringIO(
            "name,age,joined,active\n"
            "alice,30,2026-01-01,yes\n"
            "bob,25,2026-02-01,no\n"
            "cleo,,2026-03-01,yes\n"))
        s = core.summarize(header, rows)
        self.assertEqual(s["rows"], 3)
        self.assertEqual(s["cols"], 4)
        by_name = {c["name"]: c for c in s["columns"]}
        self.assertEqual(by_name["age"]["type"], "int")
        self.assertEqual(by_name["age"]["nulls"], 1)
        self.assertEqual(by_name["age"]["min"], 25)
        self.assertEqual(by_name["age"]["max"], 30)
        self.assertEqual(by_name["joined"]["type"], "date")
        self.assertEqual(by_name["active"]["type"], "bool")
        self.assertEqual(by_name["active"]["true"], 2)
        self.assertEqual(by_name["name"]["type"], "string")
        self.assertEqual(by_name["name"]["unique"], 3)

    def test_header_only_file(self):
        header, rows = core.read_rows(io.StringIO("a,b\n"))
        s = core.summarize(header, rows)
        self.assertEqual(s["rows"], 0)
        self.assertEqual([c["type"] for c in s["columns"]], ["empty", "empty"])


if __name__ == "__main__":
    unittest.main()


class TestEncodingAndLimits(unittest.TestCase):
    def test_utf16_bom_is_detected_not_misparsed(self):
        import io as _io
        data = "name,age\nalice,30\nbob,25\n".encode("utf-16-le")
        seen = []
        header, rows = core.read_rows(_io.BytesIO(b"\xff\xfe" + data),
                                      on_encoding=seen.append)
        self.assertEqual(header, ["name", "age"])
        self.assertEqual(len(rows), 2)
        self.assertEqual(seen, ["utf-16-le"])

    def test_large_field_parses_without_traceback(self):
        import io as _io
        big = "x" * 200_000
        header, rows = core.read_rows(_io.StringIO('a,b\n1,"' + big + '"\n'))
        self.assertEqual(rows[0][1], big)

    def test_oversize_field_is_a_clean_value_error(self):
        import csv as _csv
        import io as _io
        old_flag = core.FIELD_LIMIT
        old_csv_limit = _csv.field_size_limit(128)
        core.FIELD_LIMIT = 256  # max(128, 256) < 2048, so the field trips it
        try:
            with self.assertRaises(ValueError) as ctx:
                core.read_rows(_io.StringIO('a\n"' + "x" * 2048 + '"\n'))
            self.assertIn("could not parse the CSV", str(ctx.exception))
        finally:
            core.FIELD_LIMIT = old_flag
            _csv.field_size_limit(old_csv_limit)
