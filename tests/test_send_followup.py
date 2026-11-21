"""Tests for follow-up sending and the daily-cap accounting in
scripts/send_mail.py.

Two regressions are pinned here:

1. Cap double counting. A successful real send was appended to the
   send-state AND added to the run's extra counter, and the cap check
   summed both, so every real send consumed the daily cap twice
   (cap 4 delivered 2 letters). Real sends must count once.

2. Follow-ups had no send path at all: the cold path refuses anyone
   already contacted, and no other script sends. Sender.attempt_followup
   is that path, and it must re-validate eligibility at send time —
   a company that has since replied, hit the follow-up maximum, or is
   still inside the interval is refused even if it was eligible when
   the follow-up was selected.

Run from the repository root:
    python3 -m unittest discover -s tests
"""
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "scripts"))

import _config  # noqa: E402
import send_mail  # noqa: E402

BODY = ("Hi Maria,\n\n"
        "I noticed Harbour Table runs a dedicated tableware category "
        "with a B2B ordering portal for wholesale accounts.\n\n"
        "We manufacture ceramic tableware sets for wholesale and "
        "contract buyers. The range is CE certified and currently "
        "in stock at our Guangzhou warehouse.\n\n"
        "Could I send you our catalogue and wholesale terms?\n\n"
        "Best regards,\nAlex Rivera\n"
        "Guangzhou BrightTable Ceramics\n")

SMTP_ENV = {"SMTP_HOST": "mx.example.com", "SMTP_USER": "a@example.com",
            "SMTP_PASS": "secret", "SMTP_FROM": "a@example.com"}


def _days_ago(days):
    return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")


def _patch_config(**overrides):
    real_get = _config.get

    def fake_get(key, default=None):
        if key in overrides:
            return overrides[key]
        return real_get(key, default)

    return mock.patch.object(_config, "get", fake_get)


class _SenderCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = self.tmp.name
        self.feedback_path = os.path.join(root, "outreach-feedback.json")
        self.blocklist_path = os.path.join(root, "blocklist.json")
        self.state_path = os.path.join(root, "send-state.json")
        self.log_path = os.path.join(root, "send-log.jsonl")
        self.write_feedback([])
        with open(self.blocklist_path, "w", encoding="utf-8") as fh:
            json.dump({"entries": []}, fh)

    def tearDown(self):
        self.tmp.cleanup()

    def write_feedback(self, entries):
        with open(self.feedback_path, "w", encoding="utf-8") as fh:
            json.dump({"entries": entries}, fh)

    def make_sender(self, state, send=False):
        return send_mail.Sender(state, self.state_path, self.log_path,
                                self.feedback_path, send=send,
                                blocklist_path=self.blocklist_path)


class TestCapAccounting(_SenderCase):
    def test_real_sends_count_once_against_the_cap(self):
        sender = self.make_sender({"sent": [], "followups": []},
                                  send=True)
        outcomes = []
        with _patch_config(daily_send_cap=4), \
                mock.patch.object(send_mail, "_deliver",
                                  return_value=(True, "")), \
                mock.patch.dict(os.environ, SMTP_ENV):
            for i in range(4):
                outcome, reason, _ = sender.attempt(
                    f"buyer{i}@shop{i}.example.com",
                    "Wholesale enquiry", BODY, "hunter_valid",
                    f"Shop {i}", "Maria")
                outcomes.append(outcome)
        self.assertEqual(outcomes, ["sent"] * 4)
        self.assertEqual(len(sender.state["sent"]), 4)

    def test_dry_run_would_sends_still_stop_at_the_cap(self):
        sender = self.make_sender({"sent": [], "followups": []},
                                  send=False)
        outcomes = []
        with _patch_config(daily_send_cap=2):
            for i in range(3):
                outcome, _, stop = sender.attempt(
                    f"buyer{i}@shop{i}.example.com",
                    "Wholesale enquiry", BODY, "hunter_valid",
                    f"Shop {i}", "Maria")
                outcomes.append(outcome)
        self.assertEqual(outcomes, ["would_send", "would_send", "refused"])


class TestFollowup(_SenderCase):
    def _lead(self, **overrides):
        lead = {"company": "Harbour Table Co.",
                "email_status": "hunter_valid",
                "contact": "Maria Lopez",
                "followups_sent": 0,
                "last_touch_at": _days_ago(40)}
        lead.update(overrides)
        return lead

    def _state(self, fu_count=0, touch_days_ago=40):
        state = {"sent": [{
            "company": "Harbour Table Co.",
            "to": "maria.lopez@harbourtable.example.com",
            "sent_at": (datetime.now()
                        - timedelta(days=touch_days_ago)).isoformat(
                            timespec="seconds"),
            "subject": "Wholesale enquiry"}],
            "followups": [{
                "company": "Harbour Table Co.",
                "to": "maria.lopez@harbourtable.example.com",
                "sent_at": (datetime.now()
                            - timedelta(days=touch_days_ago)).isoformat(
                                timespec="seconds"),
                "subject": "Follow-up"} for _ in range(fu_count)]}
        return state

    def _attempt(self, sender, lead):
        return sender.attempt_followup(
            "maria.lopez@harbourtable.example.com",
            "Wholesale enquiry", BODY, lead, "Maria")

    def test_eligible_followup_would_send(self):
        sender = self.make_sender(self._state())
        with _patch_config(followup_max=2, followup_interval_days=30):
            outcome, reason, _ = self._attempt(sender, self._lead())
        self.assertEqual(outcome, "would_send", reason)

    def test_replied_company_is_refused_at_send_time(self):
        self.write_feedback([{
            "company": "Harbour Table Co.", "date": _days_ago(1),
            "email": "maria.lopez@harbourtable.example.com",
            "type": "reply", "summary": "Re: wholesale terms"}])
        sender = self.make_sender(self._state())
        with _patch_config(followup_max=2, followup_interval_days=30):
            outcome, reason, _ = self._attempt(sender, self._lead())
        self.assertEqual(outcome, "refused")
        self.assertIn("already replied", reason)

    def test_unsubscribed_company_is_refused(self):
        self.write_feedback([{
            "company": "Harbour Table Co.", "date": _days_ago(1),
            "email": "maria.lopez@harbourtable.example.com",
            "type": "unsubscribe", "summary": "unsubscribe"}])
        sender = self.make_sender(self._state())
        with _patch_config(followup_max=2, followup_interval_days=30):
            outcome, reason, _ = self._attempt(sender, self._lead())
        self.assertEqual(outcome, "refused")
        self.assertIn("unsubscribed", reason)

    def test_followup_maximum_is_refused(self):
        sender = self.make_sender(self._state(fu_count=2))
        with _patch_config(followup_max=2, followup_interval_days=30):
            outcome, reason, _ = self._attempt(sender, self._lead())
        self.assertEqual(outcome, "refused")
        self.assertIn("maximum", reason)

    def test_interval_not_met_is_refused(self):
        sender = self.make_sender(self._state(touch_days_ago=10))
        lead = self._lead(last_touch_at=_days_ago(10))
        with _patch_config(followup_max=2, followup_interval_days=30):
            outcome, reason, _ = self._attempt(sender, lead)
        self.assertEqual(outcome, "refused")
        self.assertIn("interval", reason)

    def test_no_prior_contact_is_refused(self):
        sender = self.make_sender({"sent": [], "followups": []})
        lead = self._lead(last_touch_at="")
        with _patch_config(followup_max=2, followup_interval_days=30):
            outcome, reason, _ = self._attempt(sender, lead)
        self.assertEqual(outcome, "refused")
        self.assertIn("no prior contact", reason)

    def test_unverified_status_is_refused(self):
        sender = self.make_sender(self._state())
        lead = self._lead(email_status="unverified")
        with _patch_config(followup_max=2, followup_interval_days=30):
            outcome, reason, _ = self._attempt(sender, lead)
        self.assertEqual(outcome, "refused")
        self.assertIn("recipient status", reason)

    def test_real_followup_is_recorded_and_counts_toward_cap(self):
        sender = self.make_sender(self._state(), send=True)
        with _patch_config(daily_send_cap=1, followup_max=2,
                           followup_interval_days=30), \
                mock.patch.object(send_mail, "_deliver",
                                  return_value=(True, "")), \
                mock.patch.dict(os.environ, SMTP_ENV):
            outcome, reason, _ = self._attempt(sender, self._lead())
            self.assertEqual(outcome, "sent", reason)
            self.assertEqual(len(sender.state["followups"]), 1)
            # The follow-up consumed the whole shared cap of 1, so a
            # cold letter to a fresh company is now refused by check 4.
            outcome2, reason2, _ = sender.attempt(
                "buyer@freshshop.example.com", "Wholesale enquiry",
                BODY, "hunter_valid", "Fresh Shop", "Maria")
        self.assertEqual(outcome2, "refused")
        self.assertIn("daily send cap", reason2)


if __name__ == "__main__":
    unittest.main()
