import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from csvpeek.cli import main


CSV = ("name,age,city\n"
       "alice,30,london\n"
       "bob,25,paris\n"
       "cleo,28,london\n")


class TestCli(unittest.TestCase):
    def run_cli(self, argv, stdin_text=None):
        out, err = io.StringIO(), io.StringIO()
        old = None
        if stdin_text is not None:
            old = __import__("sys").stdin
            __import__("sys").stdin = io.StringIO(stdin_text)
        try:
            with redirect_stdout(out), redirect_stderr(err):
                code = main(argv)
        finally:
            if old is not None:
                __import__("sys").stdin = old
        return code, out.getvalue(), err.getvalue()

    def test_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
            f.write(CSV)
            path = f.name
        try:
            code, out, err = self.run_cli([path])
        finally:
            os.unlink(path)
        self.assertEqual(code, 0)
        self.assertIn("3 rows x 3 columns", out)
        self.assertIn("alice", out)

    def test_stdin(self):
        code, out, _ = self.run_cli(["-"], stdin_text=CSV)
        self.assertEqual(code, 0)
        self.assertIn("3 rows x 3 columns", out)

    def test_no_sample(self):
        code, out, _ = self.run_cli(["-", "--rows", "0"], stdin_text=CSV)
        self.assertNotIn("first rows:", out)
        self.assertIn("age", out)

    def test_forced_delimiter(self):
        code, out, _ = self.run_cli(["-", "--delimiter", ";"], stdin_text="a;b\n1;2\n")
        self.assertEqual(code, 0)
        self.assertIn("1 rows x 2 columns", out)

    def test_missing_file_is_a_clean_error(self):
        code, out, err = self.run_cli(["/no/such/file.csv"])
        self.assertEqual(code, 2)
        self.assertIn("cannot read", err)

    def test_empty_file_is_a_clean_error(self):
        code, out, err = self.run_cli(["-"], stdin_text="")
        self.assertEqual(code, 1)
        self.assertIn("empty", err)

    def test_tab_alias(self):
        code, out, _ = self.run_cli(["-", "--delimiter", "TAB"], stdin_text="a\tb\n1\t2\n")
        self.assertIn("1 rows x 2 columns", out)


if __name__ == "__main__":
    unittest.main()
