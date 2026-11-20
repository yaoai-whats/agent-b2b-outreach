"""Tests for scripts/read_inbox.py classification.

The regression that matters most: ordinary business subjects containing
the words "delivery" or "failure" must classify as replies, never as
bounces — a false bounce loses a real buyer and feeds the sending
circuit breaker in scripts/send_mail.py.

Run from the repository root:
    python3 -m unittest discover -s tests
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "scripts"))

from read_inbox import classify  # noqa: E402


class TestClassify(unittest.TestCase):
    def test_delivery_schedule_subject_is_reply(self):
        self.assertEqual(
            classify("maria.lopez@harbourtable.example.com",
                     "Re: delivery schedule for 500 sets",
                     "Thanks, when can the first shipment leave?"),
            "reply")

    def test_failure_rate_subject_is_reply(self):
        self.assertEqual(
            classify("elin.karlsson@nordichome.example.com",
                     "Re: LED tube failure rate",
                     "Could you share the failure rate over 12 months?"),
            "reply")

    def test_mailer_daemon_sender_is_bounce(self):
        self.assertEqual(
            classify("mailer-daemon@mail.example.com",
                     "Delivery Status Notification",
                     "The following message could not be delivered."),
            "bounce")

    def test_postmaster_sender_is_bounce(self):
        self.assertEqual(
            classify("postmaster@example.com", "Returned mail",
                     "User unknown"),
            "bounce")

    def test_undeliverable_subject_from_plain_sender_is_bounce(self):
        self.assertEqual(
            classify("someone@example.com",
                     "Undeliverable: your order confirmation",
                     ""),
            "bounce")

    def test_delivery_has_failed_subject_is_bounce(self):
        self.assertEqual(
            classify("someone@example.com", "Delivery has failed", ""),
            "bounce")

    def test_dsn_structure_is_bounce(self):
        # A neutral subject from an ordinary-looking sender still counts
        # when the message structure is a delivery status notification.
        self.assertEqual(
            classify("daemon@mx.example.com", "Report", "",
                     is_dsn=True),
            "bounce")

    def test_unsubscribe_body_is_unsubscribe(self):
        self.assertEqual(
            classify("buyer@example.com", "Re: your catalogue",
                     "Please unsubscribe me from these emails."),
            "unsubscribe")

    def test_plain_reply_is_reply(self):
        self.assertEqual(
            classify("buyer@example.com", "Re: wholesale terms",
                     "Please send the price list for the spring range."),
            "reply")


if __name__ == "__main__":
    unittest.main()
