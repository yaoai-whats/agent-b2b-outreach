"""Tests for fail-closed safety data and the send lock in
scripts/send_mail.py, plus the blocklist shape guard in
scripts/read_inbox.py.

The regression that matters: safety state (blocklist, feedback,
send-state) that exists but is corrupt or the wrong shape must never
be read as "empty history". An empty blocklist re-enables barred
recipients; an empty feedback log disarms the unsubscribe/bounce
refusals and the circuit breaker; an empty send-state disarms the
daily cap. Loaders raise, and the send entry point refuses. A missing
file is different — that is a fresh start and stays allowed.

The send lock pins the concurrency rule: exactly one --send run
holds it; a second holder is refused rather than racing the first
run's checks against stale state.

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

import read_inbox  # noqa: E402
import send_mail  # noqa: E402


class TestFailClosedLoaders(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = self.tmp.name
        self.feedback_path = os.path.join(root, "outreach-feedback.json")
        self.blocklist_path = os.path.join(root, "blocklist.json")
        self.state_path = os.path.join(root, "send-state.json")
        self.log_path = os.path.join(root, "send-log.jsonl")
        with open(self.feedback_path, "w", encoding="utf-8") as fh:
            json.dump({"entries": []}, fh)
        with open(self.blocklist_path, "w", encoding="utf-8") as fh:
            json.dump({"entries": []}, fh)

    def tearDown(self):
        self.tmp.cleanup()

    def _sender(self, state=None):
        return send_mail.Sender(
            {"sent": [], "followups": []} if state is None else state,
            self.state_path, self.log_path, self.feedback_path,
            send=False, blocklist_path=self.blocklist_path)

    def test_missing_blocklist_means_no_entries(self):
        os.unlink(self.blocklist_path)
        sender = self._sender()
        self.assertEqual(sender.blocklist_entries, [])

    def test_corrupt_blocklist_raises(self):
        with open(self.blocklist_path, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        with self.assertRaises(ValueError):
            self._sender()

    def test_wrong_shape_blocklist_raises(self):
        with open(self.blocklist_path, "w", encoding="utf-8") as fh:
            json.dump([{"domain": "blocked.example.com"}], fh)
        with self.assertRaises(ValueError):
            self._sender()

    def test_corrupt_feedback_raises(self):
        with open(self.feedback_path, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        with self.assertRaises(ValueError):
            self._sender()

    def test_wrong_shape_feedback_raises(self):
        with open(self.feedback_path, "w", encoding="utf-8") as fh:
            json.dump({"entries": "oops"}, fh)
        with self.assertRaises(ValueError):
            self._sender()

    def test_wrong_shape_state_raises(self):
        with self.assertRaises(ValueError):
            self._sender(state=["not", "a", "dict"])
        with self.assertRaises(ValueError):
            self._sender(state={"sent": "oops", "followups": []})


class TestBlocklistWriteGuard(unittest.TestCase):
    def test_wrong_shape_blocklist_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, "blocklist.json")
            original = json.dumps([{"domain": "keep.example.com"}])
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(original)
            with self.assertRaises(ValueError):
                read_inbox.add_to_blocklist(
                    path, "buyer@shop.example.com", "Shop", "2026-11-20")
            with open(path, encoding="utf-8") as fh:
                self.assertEqual(fh.read(), original)


class TestSendLock(unittest.TestCase):
    def test_lock_is_exclusive_and_releasable(self):
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, "send.lock")
            fd = send_mail.acquire_send_lock(path)
            self.assertIsNotNone(fd)
            self.assertIsNone(send_mail.acquire_send_lock(path))
            send_mail.release_send_lock(fd, path)
            self.assertFalse(os.path.exists(path))
            fd2 = send_mail.acquire_send_lock(path)
            self.assertIsNotNone(fd2)
            send_mail.release_send_lock(fd2, path)


if __name__ == "__main__":
    unittest.main()
