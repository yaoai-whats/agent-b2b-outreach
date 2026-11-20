"""Tests for the exclusion check in scripts/send_mail.py (check 2).

The send path used to refuse only on verification status, the quality
gate, the daily cap, and the bounce breaker — the blocklist existed
only in the docs. These tests pin the fifth check: blocklisted
addresses and domains, recipients or companies already contacted,
unsubscribed addresses, and previously bounced addresses are all
refused before anything is sent, while a clean recipient still goes
through as a dry-run would_send.

Run from the repository root:
    python3 -m unittest discover -s tests
"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "scripts"))

import send_mail  # noqa: E402

PASSING_BODY = ("Hi Sofia,\n\n"
                "I noticed Clean Shop runs a dedicated tableware "
                "category with a B2B ordering portal for wholesale "
                "accounts.\n\n"
                "We manufacture ceramic tableware sets for wholesale "
                "and contract buyers. The range is CE certified and "
                "currently in stock at our Guangzhou warehouse.\n\n"
                "Could I send you our catalogue and wholesale terms?\n\n"
                "Best regards,\nAlex Rivera\n"
                "Guangzhou BrightTable Ceramics\n")


class TestSendExclusions(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = self.tmp.name
        self.feedback_path = os.path.join(root, "outreach-feedback.json")
        with open(self.feedback_path, "w", encoding="utf-8") as fh:
            json.dump({"entries": [
                {"company": "Nordic Home Living", "date": "2026-11-18",
                 "email": "elin.karlsson@nordichome.example.com",
                 "type": "unsubscribe", "summary": "unsubscribe"},
                {"company": "Retired Shop", "date": "2026-11-18",
                 "email": "someone@retiredshop.example.com",
                 "type": "bounce", "summary": "User unknown"},
            ]}, fh)
        self.blocklist_path = os.path.join(root, "blocklist.json")
        with open(self.blocklist_path, "w", encoding="utf-8") as fh:
            json.dump({"entries": [
                {"added_at": "2026-01-05",
                 "domain": "blockedwholesale.example.com",
                 "reason": "do_not_contact"},
                {"added_at": "2026-02-01",
                 "email": "barred@personmail.example.com",
                 "reason": "manual_bar"},
            ]}, fh)
        state = {"sent": [{
            "company": "Harbour Table Co.",
            "to": "maria.lopez@harbourtable.example.com",
            "sent_at": "2026-11-19T09:30:00",
            "subject": "Wholesale enquiry"}],
            "followups": []}
        self.sender = send_mail.Sender(
            state,
            os.path.join(root, "send-state.json"),
            os.path.join(root, "send-log.jsonl"),
            self.feedback_path,
            send=False,
            blocklist_path=self.blocklist_path)

    def tearDown(self):
        self.tmp.cleanup()

    def _attempt(self, to_addr, company):
        return self.sender.attempt(to_addr, "Wholesale enquiry",
                                   "Hello.", "public_confirmed",
                                   company, "")

    def test_already_sent_address_refused(self):
        outcome, reason, _ = self._attempt(
            "maria.lopez@harbourtable.example.com", "Harbour Table Co.")
        self.assertEqual(outcome, "refused")
        self.assertIn("already contacted", reason)
        self.assertIn("2026-11-19", reason)

    def test_already_contacted_company_refused(self):
        outcome, reason, _ = self._attempt(
            "new.person@harbourtable.example.com", "Harbour Table Co.")
        self.assertEqual(outcome, "refused")
        self.assertIn("already contacted", reason)

    def test_unsubscribed_address_refused(self):
        outcome, reason, _ = self._attempt(
            "elin.karlsson@nordichome.example.com", "Nordic Home Living")
        self.assertEqual(outcome, "refused")
        self.assertIn("unsubscribed", reason)

    def test_previously_bounced_address_refused(self):
        outcome, reason, _ = self._attempt(
            "someone@retiredshop.example.com", "Retired Shop")
        self.assertEqual(outcome, "refused")
        self.assertIn("previously bounced", reason)

    def test_blocklisted_domain_refused(self):
        outcome, reason, _ = self._attempt(
            "buyer@blockedwholesale.example.com", "Blocked Wholesale")
        self.assertEqual(outcome, "refused")
        self.assertIn("blocklist", reason)

    def test_blocklisted_email_refused(self):
        outcome, reason, _ = self._attempt(
            "barred@personmail.example.com", "Some Person")
        self.assertEqual(outcome, "refused")
        self.assertIn("blocklist", reason)

    def test_clean_recipient_would_send(self):
        self.assertIsNone(self.sender.exclusion_reason(
            "sofia@cleanshop.example.com", "Clean Shop"))
        outcome, reason, stop = self.sender.attempt(
            "sofia@cleanshop.example.com",
            "Wholesale enquiry: ceramic tableware sets",
            PASSING_BODY, "hunter_valid", "Clean Shop", "Sofia")
        self.assertEqual(outcome, "would_send")
        self.assertEqual(reason, "")
        self.assertFalse(stop)


if __name__ == "__main__":
    unittest.main()
