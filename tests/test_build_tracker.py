"""Tests for the follow-up eligibility logic in scripts/build_tracker.py.

Under the shipped cadence ([4, 7, 7], max 3, read from the example
config): a company whose last touch was 5 days ago with no follow-ups
sent is eligible for follow-up 1; one touched 2 days ago is not; one
that already received 3 follow-ups is sequence-complete.

Run from the repository root:
    python3 -m unittest discover -s tests
"""
import csv
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "scripts"))

import build_tracker  # noqa: E402


def _days_ago(days):
    return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")


class TestTrackerCadence(unittest.TestCase):
    def _run_tracker(self, leads, state):
        tmp = tempfile.mkdtemp()
        leads_path = os.path.join(tmp, "leads.jsonl")
        state_path = os.path.join(tmp, "send-state.json")
        feedback_path = os.path.join(tmp, "feedback.json")
        csv_path = os.path.join(tmp, "tracker.csv")
        md_path = os.path.join(tmp, "tracker.md")
        with open(leads_path, "w", encoding="utf-8") as fh:
            for lead in leads:
                fh.write(json.dumps(lead) + "\n")
        with open(state_path, "w", encoding="utf-8") as fh:
            json.dump(state, fh)
        with open(feedback_path, "w", encoding="utf-8") as fh:
            json.dump({"entries": []}, fh)
        argv = ["build_tracker.py", "--leads", leads_path,
                "--send-state", state_path, "--feedback", feedback_path,
                "--out-csv", csv_path, "--out-md", md_path]
        with mock.patch.object(sys, "argv", argv):
            build_tracker.main()
        with open(csv_path, encoding="utf-8-sig") as fh:
            return {row["company"]: row for row in csv.DictReader(fh)}

    def test_eligibility_follows_the_sequence(self):
        leads = [
            {"company": "Due Shop", "actionable": False},
            {"company": "Early Shop", "actionable": False},
            {"company": "Done Shop", "actionable": False},
        ]
        state = {
            "sent": [
                {"company": "Due Shop", "sent_at": _days_ago(5)},
                {"company": "Early Shop", "sent_at": _days_ago(2)},
                {"company": "Done Shop", "sent_at": _days_ago(40)},
            ],
            "followups": [
                {"company": "Done Shop", "sent_at": _days_ago(30)},
                {"company": "Done Shop", "sent_at": _days_ago(20)},
                {"company": "Done Shop", "sent_at": _days_ago(10)},
            ],
        }
        rows = self._run_tracker(leads, state)
        self.assertIn("follow-up 1 eligible",
                      rows["Due Shop"]["next_action"])
        self.assertEqual(rows["Early Shop"]["next_action"], "")
        self.assertIn("sequence complete",
                      rows["Done Shop"]["next_action"])


if __name__ == "__main__":
    unittest.main()
