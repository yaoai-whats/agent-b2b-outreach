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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the letter quality gate.")
    parser.add_argument("--subject", default="")
    parser.add_argument("--name", default="")
    parser.add_argument("--body-file", required=True,
                        help="Path to a UTF-8 text file with the letter body.")
    parser.add_argument("--url-len", type=int, default=0)
    args = parser.parse_args()
    with open(args.body_file, encoding="utf-8") as fh:
        body_text = fh.read()
    failures = check_email(args.name, args.subject, body_text, args.url_len)
    if failures:
        for reason in failures:
            print(f"GATE_FAIL: {reason}")
        sys.exit(1)
    print("GATE_PASS")
