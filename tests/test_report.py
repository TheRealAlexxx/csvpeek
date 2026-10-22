import io
import unittest

from csvpeek import core, report


def build(text):
    header, rows = core.read_rows(io.StringIO(text))
    return header, rows, core.summarize(header, rows)


class TestFit(unittest.TestCase):
    def test_short_unchanged(self):
        self.assertEqual(report.fit("abc", 10), "abc")

    def test_long_ellipsized(self):
        self.assertEqual(report.fit("abcdefghij", 7), "abcd...")

    def test_tiny_width(self):
        self.assertEqual(report.fit("abcdef", 2), "ab")


class TestRender(unittest.TestCase):
    def test_full_report(self):
        header, rows, s = build(
            "name,age,city\n"
            "alice,30,london\n"
            "bob,25,paris\n"
            "cleo,28,london\n")
        out = report.render(s, sample_rows=rows[:2], header=header)
        self.assertIn("3 rows x 3 columns", out)
        self.assertIn("name", out)
        self.assertIn("string", out)
        self.assertIn("age", out)
        self.assertIn("min 25", out)
        self.assertIn("max 30", out)
        self.assertIn("london (2)", out)
        self.assertIn("first rows:", out)
        self.assertIn("alice", out)

    def test_narrow_terminal_does_not_explode(self):
        header, rows, s = build("averylongcolumnnamethatkeepsgoing,x\n1,2\n")
        out = report.render(s, width=60, name_width=12)
        for line in out.split("\n"):
            self.assertLessEqual(len(line), 80, line)

    def test_float_formatting(self):
        self.assertEqual(report.fmt_number(2.0), "2")
        self.assertEqual(report.fmt_number(3.14159), "3.142")
        self.assertEqual(report.fmt_number(7), "7")


if __name__ == "__main__":
    unittest.main()
