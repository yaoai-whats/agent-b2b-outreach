#!/usr/bin/env python3
"""Letter quality gate: deterministic checks every letter must pass.

A letter that fails any check does not join a batch. The batch report lists
failures by company and reason so the template or the data can be fixed.

Checks:
1. No em dash or en dash in subject or body.
2. No snooping words (data sources the recipient never published for you).
3. No hype or pressure phrases.
4. No unverifiable claim phrases.
5. Greeting is clean: no brackets, no title residue, no non-name characters.
6. Body within the word limit; optional rendered link within its limit.
7. Follow-ups only (check_followup): no bare-nudge phrases ("just
   following up" and kin — a follow-up must carry new information from a
   new angle, never a content-free reminder), and the body must not be a
   near-copy of the previous letter to the same company.

Word lists are defaults only. Extend them per language and per business by
editing the lists below, by adding a "risk_claims" / "spam_phrases" /
"snooping_words" list to your config (read via scripts/_config.py), or by
pointing QUALITY_GATE_EXTRA (a JSON file with the same optional keys) at
your own additions.

Usage:
    from quality_gate import check_email
    fails = check_email(greeting_name, subject, body)

CLI:
    python3 quality_gate.py --subject "..." --name "Maria" --body-file letter.txt
    (exit code 0 = pass, 1 = fail, reasons printed one per line)
"""
import argparse
import json
import os
import re
import sys

BANNED_CHARS = ["—", "–"]  # em dash, en dash

# Data-source language that makes a recipient feel surveilled. The letter's
# observation may only use what the company publishes itself.
SNOOPING_WORDS = ["shipment", "customs record", "bill of lading",
                  "import record", "importyeti", "volza",
                  "your imports", "containers last year"]

SPAM_PHRASES = ["best price", "cheapest", "guaranteed", "risk-free",
                "risk free", "limited time", "act now", "urgent",
                "free quote", "dear sir", "dear madam",
                "to whom it may concern", "lowest price"]

# Unverifiable absolute claims. These are deliberately precise phrases:
# a bare word like "certified" or "in stock" is a normal, checkable fact
# in many industries (a product can genuinely carry a certification, a
# warehouse can genuinely hold stock), so only the absolute, unprovable
# formulations are gated.
RISK_CLAIMS = ["guaranteed certified", "certification guaranteed",
               "fully certified", "always in stock", "guaranteed delivery",
               "best price", "cheapest", "lowest price guaranteed",
               "number one", "risk-free", "100% guaranteed",
               "exclusive distributor", "existing customer",
               "approved supplier"]

MAX_WORDS = 130
MAX_URL = 1800

# Bare-nudge formulations banned in follow-ups (check_followup only).
# A follow-up earns its send with new information from a new angle; these
# phrases are the fingerprint of a content-free reminder. First touches
# are not checked against this list.
FOLLOWUP_NUDGE_PHRASES = ["just following up", "just checking in",
                          "just wanted to follow up",
                          "i am following up", "i'm following up",
                          "following up on my last",
                          "following up on my previous",
                          "checking in on my", "circling back",
                          "a gentle reminder", "just a reminder",
                          "touching base"]

# A follow-up whose word set overlaps the previous letter's at or above
# this Jaccard similarity is a re-send, not a new angle.
FOLLOWUP_MAX_SIMILARITY = 0.75


def _load_extra():
    path = os.environ.get("QUALITY_GATE_EXTRA", "")
    if not path or not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


_EXTRA = _load_extra()
SNOOPING_WORDS += _EXTRA.get("snooping_words", [])
SPAM_PHRASES += _EXTRA.get("spam_phrases", [])
RISK_CLAIMS += _EXTRA.get("risk_claims", [])

# The operator's config may carry the same extension lists; they are
# appended exactly like the QUALITY_GATE_EXTRA file above.
try:
    import _config as _cfg
    SNOOPING_WORDS += _cfg.get("snooping_words", []) or []
    SPAM_PHRASES += _cfg.get("spam_phrases", []) or []
    RISK_CLAIMS += _cfg.get("risk_claims", []) or []
except Exception:  # noqa: BLE001 - config is optional for the gate
    pass


def check_email(name, subject, body, url_len=0):
    """Return a list of failure reasons. An empty list means pass."""
    fails = []
    text = (subject or "") + "\n" + (body or "")
    low = text.lower()
    for ch in BANNED_CHARS:
        if ch in text:
            fails.append(f"contains banned dash character U+{ord(ch):04X}")
    for word in SNOOPING_WORDS:
        if word in low:
            fails.append(f"contains snooping word: {word}")
    for phrase in SPAM_PHRASES:
        if phrase in low:
            fails.append(f"contains hype phrase: {phrase}")
    for phrase in RISK_CLAIMS:
        if phrase in low:
            fails.append(f"contains unverifiable claim: {phrase}")
    if name:
        if any(c in name for c in "()[]"):
            fails.append("greeting contains bracket residue")
        if re.search(r"\b(Mr|Mrs|Ms|Dr|Manager|Director)\b\.?", name):
            fails.append("greeting contains title residue")
    words = len((body or "").split())
    if words > MAX_WORDS:
        fails.append(f"body is {words} words, limit is {MAX_WORDS}")
    if url_len > MAX_URL:
        fails.append(f"rendered link is {url_len} characters, limit is {MAX_URL}")
    return fails


def _word_set(text):
    return set(re.findall(r"[a-z0-9']+", (text or "").lower()))


def check_followup(name, subject, body, previous_body=None, url_len=0):
    """Quality gate for a follow-up letter.

    Runs every first-touch check, then the follow-up-specific ones: no
    bare-nudge phrases, and — when the previous letter's body is given —
    the follow-up must not be a near-copy of it. A follow-up that repeats
    the previous letter's angle is refused here so it gets rewritten
    with genuinely new content instead of shipped as a reminder.
    """
    fails = check_email(name, subject, body, url_len)
    low = ((subject or "") + "\n" + (body or "")).lower()
    for phrase in FOLLOWUP_NUDGE_PHRASES:
        if phrase in low:
            fails.append(f"contains bare-nudge phrase: {phrase}")
    if previous_body:
        current, previous = _word_set(body), _word_set(previous_body)
        union = current | previous
        if union:
            similarity = len(current & previous) / len(union)
            if similarity >= FOLLOWUP_MAX_SIMILARITY:
                fails.append(
                    f"follow-up body is too similar to the previous "
                    f"letter (word overlap {similarity:.2f}, limit "
                    f"{FOLLOWUP_MAX_SIMILARITY}); rewrite from a new "
                    "angle with new information")
    return fails


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the letter quality gate.")
    parser.add_argument("--subject", default="")
    parser.add_argument("--name", default="")
    parser.add_argument("--body-file", required=True,
                        help="Path to a UTF-8 text file with the letter body.")
    parser.add_argument("--url-len", type=int, default=0)
    parser.add_argument("--followup", action="store_true",
                        help="Apply the follow-up checks (bare-nudge "
                             "phrases, and similarity when --previous-file "
                             "is given) on top of the standard checks.")
    parser.add_argument("--previous-file", default="",
                        help="Path to the previous letter's body file, "
                             "for the follow-up similarity check.")
    args = parser.parse_args()
    with open(args.body_file, encoding="utf-8") as fh:
        body_text = fh.read()
    if args.followup:
        previous_text = None
        if args.previous_file:
            with open(args.previous_file, encoding="utf-8") as fh:
                previous_text = fh.read()
        failures = check_followup(args.name, args.subject, body_text,
                                  previous_text, args.url_len)
    else:
        failures = check_email(args.name, args.subject, body_text, args.url_len)
    if failures:
        for reason in failures:
            print(f"GATE_FAIL: {reason}")
        sys.exit(1)
    print("GATE_PASS")
