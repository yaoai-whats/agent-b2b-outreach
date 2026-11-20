"""Tests for scripts/quality_gate.py claim checks.

Normal, checkable business facts (a real certification, real stock)
must pass; only absolute, unverifiable formulations are gated.

Run from the repository root:
    python3 -m unittest discover -s tests
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "scripts"))

from quality_gate import check_email  # noqa: E402


class TestQualityGate(unittest.TestCase):
    def test_certified_and_in_stock_facts_pass(self):
        body = ("Hi Maria,\n\n"
                "I noticed Harbour Table Co. runs a dedicated tableware "
                "category with a B2B ordering portal for wholesale "
                "accounts.\n\n"
                "We manufacture ceramic tableware sets for wholesale "
                "and contract buyers. The range is CE certified and "
                "currently in stock at our Guangzhou warehouse.\n\n"
                "Could I send you our catalogue and wholesale terms?\n\n"
                "Best regards,\nAlex Rivera\n"
                "Guangzhou BrightTable Ceramics\n")
        self.assertEqual(
            check_email("Maria", "Wholesale enquiry: ceramic tableware sets",
                        body),
            [])

    def test_guaranteed_certified_fails(self):
        body = ("Hi Maria,\n\n"
                "Our dinnerware is guaranteed certified for every "
                "market.\n\n"
                "Could I send you our catalogue and wholesale terms?\n\n"
                "Best regards,\nAlex Rivera\n"
                "Guangzhou BrightTable Ceramics\n")
        failures = check_email("Maria", "Wholesale enquiry", body)
        self.assertTrue(failures)
        self.assertTrue(any("guaranteed certified" in f for f in failures))


if __name__ == "__main__":
    unittest.main()
