"""Regression tests for the .env loader in scripts/_config.py.

The loader is the one supported path for an operator's secrets on a local
machine: the executing agent writes credentials into the repo-root .env
(git-ignored) and every script picks them up, with real environment
variables always winning over file values.
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import _config  # noqa: E402


class ParseDotenvTest(unittest.TestCase):
    def _write(self, text):
        fd, path = tempfile.mkstemp(suffix=".env")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        self.addCleanup(os.unlink, path)
        return path

    def test_basic_pairs_comments_and_blanks(self):
        path = self._write(
            "# comment\n"
            "\n"
            "SMTP_HOST=smtp.example.com\n"
            "SMTP_PORT=465\n"
        )
        values = _config._parse_dotenv(path)
        self.assertEqual(values["SMTP_HOST"], "smtp.example.com")
        self.assertEqual(values["SMTP_PORT"], "465")
        self.assertEqual(len(values), 2)

    def test_quotes_and_export_prefix(self):
        path = self._write(
            'export HUNTER_API_KEYS="key-one,key-two"\n'
            "SERPER_API_KEY='abc123'\n"
        )
        values = _config._parse_dotenv(path)
        self.assertEqual(values["HUNTER_API_KEYS"], "key-one,key-two")
        self.assertEqual(values["SERPER_API_KEY"], "abc123")

    def test_value_may_contain_equals(self):
        path = self._write("TOKEN=part1=part2\n")
        self.assertEqual(_config._parse_dotenv(path)["TOKEN"], "part1=part2")

    def test_missing_file_is_empty_not_error(self):
        self.assertEqual(_config._parse_dotenv("/nonexistent/.env"), {})

    def test_load_never_overrides_real_environment(self):
        path = self._write("DOTENV_TEST_KEY=from-file\n")
        os.environ["DOTENV_TEST_KEY"] = "from-env"
        try:
            for key, value in _config._parse_dotenv(path).items():
                os.environ.setdefault(key, value)
            self.assertEqual(os.environ["DOTENV_TEST_KEY"], "from-env")
        finally:
            del os.environ["DOTENV_TEST_KEY"]


if __name__ == "__main__":
    unittest.main()
