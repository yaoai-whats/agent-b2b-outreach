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

from quality_gate import check_email, check_followup  # noqa: E402


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


FIRST = ("Hi Maria,\n\n"
         "I noticed Harbour Table runs a dedicated tableware category "
         "with a B2B ordering portal for wholesale accounts.\n\n"
         "We manufacture ceramic tableware sets for wholesale and "
         "contract buyers.\n\n"
         "Could I send you our catalogue and wholesale terms?\n\n"
         "Best regards,\nAlex Rivera\n"
         "Guangzhou BrightTable Ceramics\n")


class TestFollowupGate(unittest.TestCase):
    def test_bare_nudge_fails_the_followup_gate(self):
        body = ("Hi Maria,\n\n"
                "Just following up on my last email about our "
                "tableware sets.\n\n"
                "Best regards,\nAlex Rivera\n"
                "Guangzhou BrightTable Ceramics\n")
        failures = check_followup("Maria", "Wholesale enquiry", body)
        self.assertTrue(any("bare-nudge" in f for f in failures))

    def test_nudge_phrase_is_not_a_first_touch_check(self):
        body = ("Hi Maria,\n\n"
                "Just following up on my last email about our "
                "tableware sets.\n\n"
                "Best regards,\nAlex Rivera\n"
                "Guangzhou BrightTable Ceramics\n")
        self.assertEqual(check_email("Maria", "Wholesale enquiry", body),
                         [])

    def test_near_copy_of_previous_letter_fails(self):
        failures = check_followup("Maria", "Wholesale enquiry", FIRST,
                                  previous_body=FIRST)
        self.assertTrue(any("too similar" in f for f in failures))

    def test_new_angle_followup_passes(self):
        body = ("Hi Maria,\n\n"
                "Since my last note we added a stoneware breakfast "
                "set in the same glaze family as your hotel range, "
                "priced for wholesale restocking orders.\n\n"
                "Would the breakfast set be useful for your "
                "hospitality buyers?\n\n"
                "Best regards,\nAlex Rivera\n"
                "Guangzhou BrightTable Ceramics\n")
        self.assertEqual(
            check_followup("Maria", "Breakfast set for Harbour Table",
                           body, previous_body=FIRST),
            [])


if __name__ == "__main__":
    unittest.main()
