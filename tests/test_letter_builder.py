"""Regression tests for the six-skeleton letter builder.

The builder must: pick one skeleton per company deterministically by
domain hash, spread companies across skeletons, vary phrasing with
spintax, refuse a row without an observation, serve channel partners
from the partner skeleton set, and produce letters that pass the
quality gate within the word limit.
"""
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import letter_builder
from quality_gate import check_email

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SENDER = ("Alex Rivera", "Guangzhou BrightTable Ceramics")
PRODUCT = "ceramic tableware sets"
VALUE = "Chip-resistant stoneware keeps breakage in freight and storage low."


def _lead(domain, category="tableware wholesalers", **extra):
    lead = {
        "company": domain.split(".")[0].replace("-", " ").title() + " Co.",
        "domain": domain,
        "contact": "Maria Lopez",
        "buyer_category": category,
        "emails": ["buyer@" + domain],
        "observation": "runs a dedicated tableware category with a B2B ordering portal",
    }
    lead.update(extra)
    return lead


class TestSkeletonSelection(unittest.TestCase):
    def test_same_company_same_letter(self):
        lead = _lead("harbourtable.example.com")
        first = letter_builder.build_email(lead, *SENDER, PRODUCT, VALUE)
        second = letter_builder.build_email(lead, *SENDER, PRODUCT, VALUE)
        self.assertEqual(first, second)

    def test_companies_spread_across_skeletons(self):
        domains = [f"buyer{i:02d}.example.com" for i in range(20)]
        picked = {letter_builder.pick_skeleton(_lead(d)) for d in domains}
        self.assertGreaterEqual(len(picked), 3,
                                f"20 companies landed on only {picked}")

    def test_pool_narrows_by_buyer_type(self):
        gift = _lead("giftshop.example.com", category="gift retailers")
        self.assertIn(letter_builder.pick_skeleton(gift), [1, 2, 3, 5])
        retail = _lead("retailchain.example.com", category="retail chains")
        self.assertIn(letter_builder.pick_skeleton(retail), [1, 2, 3, 6])
        wholesale = _lead("wholesale.example.com",
                          category="tableware wholesalers")
        self.assertIn(letter_builder.pick_skeleton(wholesale), [1, 2, 4, 6])

    def test_all_six_skeletons_render(self):
        fields = dict(first_name="Maria", company="Skeleton Co.",
                      company_short="Skeleton Co.", observation="x.",
                      obs_first="x.", product=PRODUCT, product_value=VALUE,
                      sender_name=SENDER[0], sender_company=SENDER[1],
                      PARTNER_EXTRA=letter_builder.PARTNER_EXTRA)
        for number, skel in letter_builder.SKELETONS.items():
            lead = _lead(f"skeleton{number}.example.com")
            rendered_subj = letter_builder._spin(
                skel["subject"], lead, 31).format(**fields)
            rendered_body = letter_builder._spin(
                skel["body"], lead, 41).format(**fields)
            for rendered in (rendered_subj, rendered_body):
                self.assertNotIn("{", rendered)
                self.assertNotIn("}", rendered)
                self.assertNotIn("|", rendered)
                self.assertNotIn("—", rendered)
        for number, skel in letter_builder.PARTNER_SKELETONS.items():
            lead = _lead(f"partner{number}.example.com")
            rendered_subj = letter_builder._spin(
                skel["subject"], lead, 31).format(**fields)
            rendered_body = letter_builder._spin(
                skel["body"], lead, 41).format(**fields)
            for rendered in (rendered_subj, rendered_body):
                self.assertNotIn("{", rendered)
                self.assertNotIn("}", rendered)
                self.assertNotIn("|", rendered)
                self.assertNotIn("—", rendered)


class TestSpintax(unittest.TestCase):
    def test_spin_picks_one_option(self):
        lead = _lead("spin.example.com")
        out = letter_builder._spin("{alpha|beta|gamma} and {delta|epsilon}",
                                   lead, 7)
        self.assertTrue(out.startswith(("alpha", "beta", "gamma")))
        self.assertNotIn("{", out)

    def test_spin_leaves_placeholders_alone(self):
        lead = _lead("spin.example.com")
        out = letter_builder._spin("Hi {name}, {We make {product}|We supply {product}}.",
                                   lead, 7)
        self.assertIn("{name}", out)
        self.assertIn("{product}", out)
        self.assertNotIn("|", out)

    def test_no_unrendered_braces_in_built_letter(self):
        for i in range(12):
            lead = _lead(f"brace{i:02d}.example.com")
            _, subject, body = letter_builder.build_email(
                lead, *SENDER, PRODUCT, VALUE)
            self.assertNotIn("{", subject + body)
            self.assertNotIn("}", subject + body)
            self.assertNotIn("|", subject + body)


class TestObservationRule(unittest.TestCase):
    def test_missing_observation_refuses(self):
        lead = _lead("noobs.example.com", observation="")
        with self.assertRaises(ValueError):
            letter_builder.build_email(lead, *SENDER, PRODUCT, VALUE)

    def test_explicit_observation_overrides_row(self):
        lead = _lead("override.example.com", observation="")
        _, _, body = letter_builder.build_email(
            lead, *SENDER, PRODUCT, VALUE,
            observation="lists a tableware range for hotels")
        self.assertIn("lists a tableware range for hotels", body)


class TestPartnerSkeletons(unittest.TestCase):
    def test_partner_letter_uses_partner_angle(self):
        lead = _lead("partner.example.com", is_channel_partner=True)
        _, _, body = letter_builder.build_email(
            lead, *SENDER, PRODUCT, VALUE)
        self.assertIn("partner", body.lower())
        # Every partner skeleton carries the partner angle; the five
        # longer ones carry the full partner-range sentence, while the
        # three-line short skeleton (3) keeps its length band and names
        # the partner range instead.
        fields = dict(first_name="Maria", company="Partner Co.",
                      company_short="Partner Co.", observation="x.",
                      obs_first="x.", product=PRODUCT, product_value=VALUE,
                      sender_name=SENDER[0], sender_company=SENDER[1],
                      PARTNER_EXTRA=letter_builder.PARTNER_EXTRA)
        for number, skel in letter_builder.PARTNER_SKELETONS.items():
            rendered = letter_builder._spin(
                skel["body"], lead, 41).format(**fields)
            self.assertIn("partner", rendered.lower())
            if number == 3:
                self.assertIn("partner ranges", rendered)
            else:
                self.assertIn(letter_builder.PARTNER_EXTRA, rendered)

    def test_partner_skeleton_stable_per_company(self):
        lead = _lead("partner.example.com", is_channel_partner=True)
        first = letter_builder.build_email(lead, *SENDER, PRODUCT, VALUE)
        second = letter_builder.build_email(lead, *SENDER, PRODUCT, VALUE)
        self.assertEqual(first, second)


class TestGateAndLimits(unittest.TestCase):
    def test_built_letters_pass_quality_gate(self):
        for i in range(12):
            lead = _lead(f"gate{i:02d}.example.com")
            _, subject, body = letter_builder.build_email(
                lead, *SENDER, PRODUCT, VALUE)
            fails = check_email("Maria", subject, body)
            self.assertEqual(fails, [], f"gate failed for {lead['domain']}: {fails}")
            self.assertLessEqual(len(body.split()), 130)

    def test_cli_builds_example_lead(self):
        proc = subprocess.run(
            [sys.executable, "scripts/letter_builder.py",
             "--lead", "data/leads.example.jsonl", "--line", "1"],
            cwd=REPO, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("To: maria.lopez@harbourtable.example.com", proc.stdout)
        self.assertIn("Subject:", proc.stdout)


if __name__ == "__main__":
    unittest.main()
