"""Tests for DSN bounce attribution in scripts/read_inbox.py.

The regression that matters: a delivery status notification comes
From a mailer-daemon, but the address that failed is named inside the
DSN (Final-Recipient). Recording the daemon as the feedback email
left the real customer address unrefused on the sending side and the
company unmatched. These tests pin the attribution: one feedback
entry per failed recipient, keyed by that recipient; delayed
recipients recorded as "delayed", never as bounces; success receipts
recorded not at all; a bounce with no parseable recipient falls back
to the sender-keyed entry a human can match.

Run from the repository root:
    python3 -m unittest discover -s tests
"""
import email
import email.policy
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "scripts"))

import read_inbox  # noqa: E402

COMPANIES = {"maria.lopez@harbourtable.example.com": "Harbour Table Co.",
             "elin.karlsson@nordichome.example.com": "Nordic Home Living AB"}


def _msg(raw):
    return email.message_from_string(raw, policy=email.policy.default)


def _dsn(recipient_blocks):
    blocks = "\n\n".join(recipient_blocks)
    return (
        "From: MAILER-DAEMON@mx.example.com\n"
        "To: sender@example.com\n"
        "Subject: Delivery Status Notification (Failure)\n"
        "Date: Thu, 20 Nov 2026 10:00:00 +0000\n"
        "MIME-Version: 1.0\n"
        'Content-Type: multipart/report; report-type=delivery-status; '
        'boundary="B"\n'
        "\n"
        "--B\n"
        "Content-Type: text/plain\n"
        "\n"
        "Delivery to the following recipient failed.\n"
        "\n"
        "--B\n"
        "Content-Type: message/delivery-status\n"
        "\n"
        "Reporting-MTA: dns; mx.example.com\n"
        "\n"
        f"{blocks}\n"
        "\n"
        "--B--\n")


class TestDsnAttribution(unittest.TestCase):
    def test_failed_recipient_is_attributed_not_the_daemon(self):
        msg = _msg(_dsn([
            "Final-Recipient: rfc822; maria.lopez@harbourtable.example.com\n"
            "Action: failed\n"
            "Status: 5.1.1"]))
        entries = read_inbox.feedback_entries_for(msg, COMPANIES)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["email"],
                         "maria.lopez@harbourtable.example.com")
        self.assertEqual(entries[0]["company"], "Harbour Table Co.")
        self.assertEqual(entries[0]["type"], "bounce")

    def test_multiple_failed_recipients_each_get_an_entry(self):
        msg = _msg(_dsn([
            "Final-Recipient: rfc822; maria.lopez@harbourtable.example.com\n"
            "Action: failed\n"
            "Status: 5.1.1",
            "Final-Recipient: rfc822; elin.karlsson@nordichome.example.com\n"
            "Action: failed\n"
            "Status: 5.2.0"]))
        entries = read_inbox.feedback_entries_for(msg, COMPANIES)
        self.assertEqual([e["email"] for e in entries], [
            "maria.lopez@harbourtable.example.com",
            "elin.karlsson@nordichome.example.com"])
        self.assertTrue(all(e["type"] == "bounce" for e in entries))

    def test_delayed_recipient_is_delayed_not_bounce(self):
        msg = _msg(_dsn([
            "Final-Recipient: rfc822; elin.karlsson@nordichome.example.com\n"
            "Action: delayed\n"
            "Status: 4.2.2"]))
        entries = read_inbox.feedback_entries_for(msg, COMPANIES)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["type"], "delayed")
        self.assertEqual(entries[0]["email"],
                         "elin.karlsson@nordichome.example.com")

    def test_success_receipt_records_nothing(self):
        msg = _msg(_dsn([
            "Final-Recipient: rfc822; maria.lopez@harbourtable.example.com\n"
            "Action: delivered\n"
            "Status: 2.0.0"]))
        self.assertEqual(read_inbox.feedback_entries_for(msg, COMPANIES),
                         [])

    def test_original_recipient_is_the_fallback_field(self):
        msg = _msg(_dsn([
            "Original-Recipient: rfc822; maria.lopez@harbourtable.example.com\n"
            "Action: failed\n"
            "Status: 5.1.1"]))
        entries = read_inbox.feedback_entries_for(msg, COMPANIES)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["email"],
                         "maria.lopez@harbourtable.example.com")

    def test_daemon_bounce_without_dsn_falls_back_to_sender(self):
        msg = _msg(
            "From: mailer-daemon@mail.example.com\n"
            "Subject: Delivery Status Notification\n"
            "Date: Thu, 20 Nov 2026 10:00:00 +0000\n"
            "Content-Type: text/plain\n"
            "\n"
            "The following message could not be delivered.\n")
        entries = read_inbox.feedback_entries_for(msg, COMPANIES)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["email"], "mailer-daemon@mail.example.com")
        self.assertEqual(entries[0]["company"], "")
        self.assertEqual(entries[0]["type"], "bounce")

    def test_body_text_recipient_line_is_used_when_no_dsn_part(self):
        msg = _msg(
            "From: mailer-daemon@mail.example.com\n"
            "Subject: Returned mail: user unknown\n"
            "Date: Thu, 20 Nov 2026 10:00:00 +0000\n"
            "Content-Type: text/plain\n"
            "\n"
            "Final-Recipient: rfc822; maria.lopez@harbourtable.example.com\n"
            "Action: failed\n")
        entries = read_inbox.feedback_entries_for(msg, COMPANIES)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["email"],
                         "maria.lopez@harbourtable.example.com")
        self.assertEqual(entries[0]["type"], "bounce")

    def test_plain_reply_still_keys_by_sender(self):
        msg = _msg(
            "From: Maria Lopez <maria.lopez@harbourtable.example.com>\n"
            "Subject: Re: wholesale terms\n"
            "Date: Thu, 20 Nov 2026 11:00:00 +0000\n"
            "Content-Type: text/plain\n"
            "\n"
            "Please send the price list for the spring range.\n")
        entries = read_inbox.feedback_entries_for(msg, COMPANIES)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["type"], "reply")
        self.assertEqual(entries[0]["company"], "Harbour Table Co.")


if __name__ == "__main__":
    unittest.main()
