"""Tests for the follow-up cadence helpers in scripts/_config.py.

The shipped cadence is a sequence (followup_intervals_days [4, 7, 7],
followup_max 3). A config that still carries only the legacy flat
followup_interval_days must fold into a flat sequence of the same
length, so existing operators keep the cadence they configured
(migration path documented in docs/05-followup-policy.md).

Run from the repository root:
    python3 -m unittest discover -s tests
"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "scripts"))

import _config  # noqa: E402


def _with_config(values):
    def fake_get(key, default=None):
        return values.get(key, default)
    return mock.patch.object(_config, "get", fake_get)


class TestFollowupCadence(unittest.TestCase):
    def test_sequence_config(self):
        with _with_config({"followup_intervals_days": [4, 7, 7],
                           "followup_max": 3}):
            self.assertEqual(_config.followup_intervals(), [4, 7, 7])
            self.assertEqual(_config.followup_max(), 3)

    def test_max_defaults_to_sequence_length(self):
        with _with_config({"followup_intervals_days": [4, 7, 7]}):
            self.assertEqual(_config.followup_max(), 3)

    def test_legacy_flat_interval_folds(self):
        with _with_config({"followup_interval_days": 30,
                           "followup_max": 2}):
            self.assertEqual(_config.followup_intervals(), [30, 30])
            self.assertEqual(_config.followup_max(), 2)

    def test_no_keys_uses_legacy_defaults(self):
        with _with_config({}):
            self.assertEqual(_config.followup_intervals(), [30, 30])
            self.assertEqual(_config.followup_max(), 2)

    def test_short_sequence_extends_by_repeating_last(self):
        with _with_config({"followup_intervals_days": [4, 7],
                           "followup_max": 3}):
            self.assertEqual(_config.followup_intervals(), [4, 7, 7])


if __name__ == "__main__":
    unittest.main()
