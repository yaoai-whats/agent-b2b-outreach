#!/usr/bin/env python3
"""Email naming-pattern detection and candidate generation.

Pure standard library. This mechanises rung 3 of the verification
ladder in docs/03-email-verification.md: a company's email pattern
counts as established only when at least two real, published addresses
at the domain reproduce it exactly. A single example establishes
nothing, and a tie between two patterns is reported as not established
rather than guessed.

Names are normalised before use: lowercased, accents stripped
(unicodedata decomposition, so "José" becomes "jose"), and everything
outside a-z dropped.

Usage as a module:
    from email_pattern import detect, candidate
    detect([{"first": "Jane", "last": "Doe",
             "email": "jane.doe@example.com"}])
    candidate("Max", "Mustermann", "first.last", "example.com")

CLI:
    python3 email_pattern.py detect --pairs pairs.json
        pairs.json is a JSON list of {"first", "last", "email"} objects.
    python3 email_pattern.py candidate --first Jane --last Doe \
        --pattern first.last --domain example.com

Both subcommands print one JSON object. Bad arguments exit non-zero.
"""
import argparse
import json
import sys
import unicodedata


def _normalize(name):
    """Lowercase, strip accents, keep only a-z."""
    decomposed = unicodedata.normalize("NFKD", name or "")
    unmarked = "".join(c for c in decomposed
                       if not unicodedata.combining(c))
    return "".join(c for c in unmarked.lower() if "a" <= c <= "z")


# Pattern name -> local-part builder from normalised (first, last).
# Extend this table when a new real-world format shows up; detection
# and candidate generation both read it, so one entry is enough.
PATTERNS = {
    "first.last": lambda f, l: f"{f}.{l}",
    "firstlast": lambda f, l: f"{f}{l}",
    "first": lambda f, l: f"{f}",
    "f.last": lambda f, l: f"{f[:1]}.{l}",
    "flast": lambda f, l: f"{f[:1]}{l}",
    "first_last": lambda f, l: f"{f}_{l}",
    "first-last": lambda f, l: f"{f}-{l}",
    "last.first": lambda f, l: f"{l}.{f}",
    "lastfirst": lambda f, l: f"{l}{f}",
    "f_last": lambda f, l: f"{f[:1]}_{l}",
}

MIN_SUPPORT = 2


def detect(pairs):
    """Detect the email pattern behind known name/address pairs.

    pairs: an iterable of {"first", "last", "email"} dicts. Pairs whose
    names normalise to nothing, or whose email has no local part, are
    skipped. Returns a dict:
        {"established": bool, "pattern": name or None,
         "support": int, "samples": [email, ...], "reason": str}
    "established" is True only when one pattern reproduces at least
    MIN_SUPPORT pairs and no other pattern ties with it.
    """
    counts = {}
    for pair in pairs or []:
        if not isinstance(pair, dict):
            continue
        first = _normalize(pair.get("first"))
        last = _normalize(pair.get("last"))
        email = (pair.get("email") or "").strip().lower()
        local = email.split("@", 1)[0] if "@" in email else ""
        if not first or not last or not local:
            continue
        for name, render in PATTERNS.items():
            if render(first, last) == local:
                counts.setdefault(name, []).append(email)
    if not counts:
        return {"established": False, "pattern": None, "support": 0,
                "samples": [],
                "reason": "no pair reproduces any known pattern"}
    best = max(len(v) for v in counts.values())
    leaders = sorted(n for n, v in counts.items() if len(v) == best)
    if best < MIN_SUPPORT:
        return {"established": False, "pattern": None, "support": best,
                "samples": counts[leaders[0]],
                "reason": f"best pattern {leaders[0]!r} is reproduced by "
                          f"only {best} address(es); at least "
                          f"{MIN_SUPPORT} are required"}
    if len(leaders) > 1:
        return {"established": False, "pattern": None, "support": best,
                "samples": [],
                "reason": "tie between patterns "
                          + " and ".join(repr(n) for n in leaders)
                          + f" at {best} addresses each; not established"}
    name = leaders[0]
    return {"established": True, "pattern": name, "support": best,
            "samples": counts[name], "reason": ""}


def candidate(first, last, pattern, domain):
    """Render one candidate address from a name, pattern, and domain.

    Raises ValueError for an unknown pattern, a name that normalises
    to nothing, or an unusable domain. The result is a candidate only:
    it still has to climb the verification ladder before it may be
    labelled sendable.
    """
    if pattern not in PATTERNS:
        raise ValueError(f"unknown pattern {pattern!r}; known patterns: "
                         + ", ".join(sorted(PATTERNS)))
    f = _normalize(first)
    l = _normalize(last)
    if not f or not l:
        raise ValueError("first and last name must each contain at "
                         "least one a-z letter after normalisation")
    domain = (domain or "").strip().lower()
    if not domain or "@" in domain or " " in domain or "." not in domain:
        raise ValueError(f"unusable domain: {domain!r}")
    return f"{PATTERNS[pattern](f, l)}@{domain}"


def _fail(message):
    print(json.dumps({"error": message}, ensure_ascii=False),
          file=sys.stderr)
    return 2


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Detect a company's email naming pattern from "
                    "known addresses, or generate one candidate "
                    "address from a pattern.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_detect = sub.add_parser(
        "detect", help="detect the pattern behind known name/email pairs")
    p_detect.add_argument(
        "--pairs", required=True,
        help="path to a JSON file holding a list of "
             '{"first", "last", "email"} objects')
    p_cand = sub.add_parser(
        "candidate", help="generate one candidate address")
    p_cand.add_argument("--first", required=True)
    p_cand.add_argument("--last", required=True)
    p_cand.add_argument("--pattern", required=True,
                        help="one of: " + ", ".join(sorted(PATTERNS)))
    p_cand.add_argument("--domain", required=True)
    args = parser.parse_args(argv)

    if args.cmd == "detect":
        try:
            with open(args.pairs, encoding="utf-8") as fh:
                pairs = json.load(fh)
        except OSError as exc:
            return _fail(f"cannot read pairs file: {exc}")
        except ValueError as exc:
            return _fail(f"pairs file is not valid JSON: {exc}")
        if not isinstance(pairs, list):
            return _fail('pairs file must hold a JSON list of '
                         '{"first", "last", "email"} objects')
        print(json.dumps(detect(pairs), ensure_ascii=False))
        return 0
    try:
        email = candidate(args.first, args.last, args.pattern, args.domain)
    except ValueError as exc:
        return _fail(str(exc))
    print(json.dumps({"email": email}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
