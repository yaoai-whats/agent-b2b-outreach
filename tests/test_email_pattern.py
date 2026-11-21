"""Tests for scripts/email_pattern.py.

The detection rules are the safety property of the enrichment stage:
a pattern counts as established only when at least two real addresses
reproduce it exactly, and a tie is reported as not established rather
than guessed. These tests pin those rules plus name normalisation
(accents stripped, so José matches jose) and the CLI surface.

Run from the repository root:
    python3 -m unittest discover -s tests
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "scripts"))

from email_pattern import PATTERNS, candidate, detect  # noqa: E402

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "..", "scripts", "email_pattern.py")


class TestDetect(unittest.TestCase):
    def test_two_pairs_establish_first_last(self):
        result = detect([
            {"first": "Jane", "last": "Doe",
             "email": "jane.doe@brighttable.example"},
            {"first": "John", "last": "Smith",
             "email": "john.smith@brighttable.example"},
        ])
        self.assertTrue(result["established"])
        self.assertEqual(result["pattern"], "first.last")
        self.assertEqual(result["support"], 2)
        self.assertEqual(result["samples"],
                         ["jane.doe@brighttable.example",
                          "john.smith@brighttable.example"])

    def test_single_pair_does_not_establish(self):
        result = detect([
            {"first": "Jane", "last": "Doe",
             "email": "jane.doe@brighttable.example"},
        ])
        self.assertFalse(result["established"])
        self.assertIsNone(result["pattern"])
        self.assertEqual(result["support"], 1)
        self.assertIn("at least 2", result["reason"])

    def test_tie_between_patterns_does_not_establish(self):
        # first == last makes first.last and last.first render the same
        # local part; two such pairs tie both patterns at support 2.
        result = detect([
            {"first": "Sam", "last": "Sam",
             "email": "sam.sam@brighttable.example"},
            {"first": "Kim", "last": "Kim",
             "email": "kim.kim@brighttable.example"},
        ])
        self.assertFalse(result["established"])
        self.assertIsNone(result["pattern"])
        self.assertEqual(result["support"], 2)
        self.assertIn("tie", result["reason"])

    def test_unrelated_local_part_establishes_nothing(self):
        result = detect([
            {"first": "Jane", "last": "Doe",
             "email": "sales-team@brighttable.example"},
            {"first": "John", "last": "Smith",
             "email": "office@brighttable.example"},
        ])
        self.assertFalse(result["established"])
        self.assertEqual(result["support"], 0)

    def test_accented_names_match_unaccented_addresses(self):
        result = detect([
            {"first": "José", "last": "García",
             "email": "jose.garcia@brighttable.example"},
            {"first": "María", "last": "López",
             "email": "maria.lopez@brighttable.example"},
        ])
        self.assertTrue(result["established"])
        self.assertEqual(result["pattern"], "first.last")

    def test_unusable_pairs_are_skipped(self):
        result = detect([
            {"first": "", "last": "Doe",
             "email": "jane.doe@brighttable.example"},
            {"first": "Jane", "last": "Doe", "email": "not-an-email"},
            "not-a-dict",
        ])
        self.assertFalse(result["established"])
        self.assertEqual(result["support"], 0)


class TestCandidate(unittest.TestCase):
    EXPECTED = {
        "first.last": "jane.doe@example.com",
        "firstlast": "janedoe@example.com",
        "first": "jane@example.com",
        "f.last": "j.doe@example.com",
        "flast": "jdoe@example.com",
        "first_last": "jane_doe@example.com",
        "first-last": "jane-doe@example.com",
        "last.first": "doe.jane@example.com",
        "lastfirst": "doejane@example.com",
        "f_last": "j_doe@example.com",
    }

    def test_every_pattern_renders_as_expected(self):
        self.assertEqual(set(self.EXPECTED), set(PATTERNS))
        for pattern, expected in self.EXPECTED.items():
            with self.subTest(pattern=pattern):
                self.assertEqual(
                    candidate("Jane", "Doe", pattern, "example.com"),
                    expected)

    def test_accents_are_stripped(self):
        self.assertEqual(
            candidate("José", "García", "first.last", "example.com"),
            "jose.garcia@example.com")

    def test_unknown_pattern_raises(self):
        with self.assertRaises(ValueError):
            candidate("Jane", "Doe", "lastfirstdot", "example.com")

    def test_unusable_inputs_raise(self):
        with self.assertRaises(ValueError):
            candidate("123", "Doe", "first.last", "example.com")
        with self.assertRaises(ValueError):
            candidate("Jane", "Doe", "first.last", "not a domain")


class TestCli(unittest.TestCase):
    def _run(self, *argv):
        return subprocess.run(
            [sys.executable, SCRIPT, *argv],
            capture_output=True, text=True, timeout=30)

    def test_detect_cli(self):
        pairs = [
            {"first": "Jane", "last": "Doe",
             "email": "jane.doe@brighttable.example"},
            {"first": "John", "last": "Smith",
             "email": "john.smith@brighttable.example"},
        ]
        with tempfile.NamedTemporaryFile(
                "w", suffix=".json", delete=False,
                encoding="utf-8") as fh:
            json.dump(pairs, fh)
            path = fh.name
        try:
            proc = self._run("detect", "--pairs", path)
        finally:
            os.unlink(path)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        result = json.loads(proc.stdout)
        self.assertTrue(result["established"])
        self.assertEqual(result["pattern"], "first.last")

    def test_candidate_cli(self):
        proc = self._run("candidate", "--first", "Jane", "--last", "Doe",
                         "--pattern", "first.last",
                         "--domain", "example.com")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout),
                         {"email": "jane.doe@example.com"})

    def test_candidate_cli_bad_pattern_exits_nonzero(self):
        proc = self._run("candidate", "--first", "Jane", "--last", "Doe",
                         "--pattern", "nope", "--domain", "example.com")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("unknown pattern", proc.stderr)

    def test_detect_cli_missing_file_exits_nonzero(self):
        proc = self._run("detect", "--pairs", "/nonexistent/pairs.json")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("cannot read pairs file", proc.stderr)


if __name__ == "__main__":
    unittest.main()
